"""
Chemical Saver - Dosage Optimization Backend
Corva Dev Center Serverless Python Application
Developer: PRABHAT

This module calculates optimal chemical injection rates based on real-time
production data and user-defined settings.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Corva SDK imports
from corva import Api, Cache, Logger, StreamTimeEvent, stream


# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

class StatusFlag(Enum):
    """Status flags for dosage optimization results."""
    OPTIMAL = "OPTIMAL"
    OVER_DOSING = "OVER_DOSING"
    UNDER_DOSING = "UNDER_DOSING"
    PUMP_OFF = "PUMP_OFF"
    ERROR = "ERROR"
    NO_DATA = "NO_DATA"


@dataclass
class DefaultSettings:
    """Default values for well settings if not configured."""
    TARGET_PPM: int = 200
    CHEMICAL_DENSITY: float = 1.0  # kg/L
    ACTIVE_INTENSITY: float = 100.0  # %
    COST_PER_GALLON: float = 10.0  # USD (safe default)
    MIN_PUMP_RATE: float = 0.5  # GPD
    MAX_PUMP_RATE: float = 50.0  # GPD


# Conversion constants
WATER_LBS_PER_BBL = 350.0
KG_TO_LBS = 2.20462
LITERS_PER_GALLON = 3.78541
PPM_DIVISOR = 1_000_000

# Safety thresholds
SPIKE_THRESHOLD_PERCENT = 500
NO_DATA_TIMEOUT_SECONDS = 300
UNDER_DOSE_THRESHOLD_PERCENT = 10


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ProductionData:
    """Validated production data from streaming input."""
    timestamp: int
    gross_fluid_rate: float
    water_cut: float
    current_injection_rate: float
    pump_status: bool

    @classmethod
    def from_record(cls, record: Dict[str, Any], last_valid_water_cut: float = 50.0) -> 'ProductionData':
        """Create ProductionData from a raw Corva record with validation."""
        # Handle both dict and object-style records
        if hasattr(record, 'data'):
            data = record.data
            timestamp = record.timestamp
        else:
            data = record
            timestamp = record.get('timestamp', int(datetime.now().timestamp()))

        gross_fluid_rate = float(data.get('gross_fluid_rate', 0) or 0)

        water_cut = data.get('water_cut')
        if water_cut is None or not (0 <= float(water_cut) <= 100):
            water_cut = last_valid_water_cut
        else:
            water_cut = float(water_cut)

        current_injection_rate = float(data.get('current_injection_rate', 0) or 0)
        pump_status = gross_fluid_rate > 0

        return cls(
            timestamp=timestamp,
            gross_fluid_rate=gross_fluid_rate,
            water_cut=water_cut,
            current_injection_rate=current_injection_rate,
            pump_status=pump_status
        )


@dataclass
class WellSettings:
    """User-configured settings for a specific well."""
    target_ppm: int
    chemical_density: float
    active_intensity: float
    cost_per_gallon: float
    min_pump_rate: float
    max_pump_rate: float

    @classmethod
    def from_database(cls, settings: Optional[Dict[str, Any]]) -> 'WellSettings':
        """Create WellSettings from database record or use defaults."""
        defaults = DefaultSettings()

        if not settings:
            return cls(
                target_ppm=defaults.TARGET_PPM,
                chemical_density=defaults.CHEMICAL_DENSITY,
                active_intensity=defaults.ACTIVE_INTENSITY,
                cost_per_gallon=defaults.COST_PER_GALLON,
                min_pump_rate=defaults.MIN_PUMP_RATE,
                max_pump_rate=defaults.MAX_PUMP_RATE
            )

        return cls(
            target_ppm=int(settings.get('target_ppm', defaults.TARGET_PPM)),
            chemical_density=float(settings.get('chemical_density', defaults.CHEMICAL_DENSITY)),
            active_intensity=float(settings.get('active_intensity', defaults.ACTIVE_INTENSITY)),
            cost_per_gallon=float(settings.get('cost_per_gallon', defaults.COST_PER_GALLON)),
            min_pump_rate=float(settings.get('min_pump_rate', defaults.MIN_PUMP_RATE)),
            max_pump_rate=float(settings.get('max_pump_rate', defaults.MAX_PUMP_RATE))
        )


@dataclass
class OptimizationResult:
    """Output result from the optimization calculation."""
    timestamp: int
    recommended_rate_gpd: float
    actual_rate_gpd: float
    savings_opportunity_usd: float
    status_flag: str
    water_bpd: float
    current_ppm: float
    target_ppm: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'timestamp': self.timestamp,
            'recommended_rate_gpd': round(self.recommended_rate_gpd, 3) if self.recommended_rate_gpd else None,
            'actual_rate_gpd': round(self.actual_rate_gpd, 3),
            'savings_opportunity_usd': round(self.savings_opportunity_usd, 2) if self.savings_opportunity_usd else None,
            'status_flag': self.status_flag,
            'water_bpd': round(self.water_bpd, 2) if self.water_bpd else None,
            'current_ppm': round(self.current_ppm, 1) if self.current_ppm else None,
            'target_ppm': self.target_ppm
        }


# =============================================================================
# CORE OPTIMIZATION LOGIC
# =============================================================================

class ChemicalOptimizer:
    """Core optimization engine for chemical dosage calculations."""

    def __init__(self, settings: WellSettings):
        self.settings = settings
        self._last_valid_water_cut = 50.0
        self._last_data_timestamp = None

    def validate_and_filter(self, data: ProductionData, previous_rate: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """Step 1: Data Validation & Cleaning"""
        if self._last_data_timestamp:
            time_diff = data.timestamp - self._last_data_timestamp
            if time_diff > NO_DATA_TIMEOUT_SECONDS:
                return False, "NO_DATA_TIMEOUT"

        if previous_rate is not None and previous_rate > 0:
            change_percent = abs(data.gross_fluid_rate - previous_rate) / previous_rate * 100
            if change_percent > SPIKE_THRESHOLD_PERCENT:
                Logger.warning(f"Spike detected: {change_percent:.1f}% change")
                return False, "SPIKE_DETECTED"

        self._last_data_timestamp = data.timestamp
        if 0 <= data.water_cut <= 100:
            self._last_valid_water_cut = data.water_cut

        return True, None

    def calculate_water_volume(self, data: ProductionData) -> float:
        """Step 2: Calculate Water Volume"""
        return data.gross_fluid_rate * (data.water_cut / 100)

    def calculate_required_chemical_volume(self, water_bpd: float) -> float:
        """Step 3: Calculate Required Chemical Volume"""
        if water_bpd <= 0:
            return 0.0

        water_mass_lbs = water_bpd * WATER_LBS_PER_BBL
        pure_chemical_mass_lbs = water_mass_lbs * (self.settings.target_ppm / PPM_DIVISOR)

        intensity_factor = max(self.settings.active_intensity / 100, 0.01)
        gross_chemical_mass_lbs = pure_chemical_mass_lbs / intensity_factor

        gross_chemical_mass_kg = gross_chemical_mass_lbs / KG_TO_LBS
        volume_liters = gross_chemical_mass_kg / self.settings.chemical_density
        volume_gallons = volume_liters / LITERS_PER_GALLON

        return volume_gallons

    def apply_constraints(self, recommended_gpd: float) -> float:
        """Step 4: Apply Constraints"""
        if recommended_gpd <= 0:
            return 0.0
        return max(self.settings.min_pump_rate, min(recommended_gpd, self.settings.max_pump_rate))

    def calculate_financial_impact(self, current_rate: float, recommended_rate: float) -> float:
        """Step 5: Calculate Financial Impact"""
        return (current_rate - recommended_rate) * self.settings.cost_per_gallon

    def determine_status(self, data: ProductionData, recommended_rate: float) -> str:
        """Determine the status flag based on current state."""
        if not data.pump_status or data.gross_fluid_rate <= 0:
            return StatusFlag.PUMP_OFF.value

        if recommended_rate <= 0:
            return StatusFlag.PUMP_OFF.value

        diff_percent = ((data.current_injection_rate - recommended_rate) / recommended_rate) * 100

        if diff_percent > UNDER_DOSE_THRESHOLD_PERCENT:
            return StatusFlag.OVER_DOSING.value
        elif diff_percent < -UNDER_DOSE_THRESHOLD_PERCENT:
            return StatusFlag.UNDER_DOSING.value

        return StatusFlag.OPTIMAL.value

    def calculate_current_ppm(self, data: ProductionData, water_bpd: float) -> float:
        """Calculate the current PPM based on actual injection rate."""
        if water_bpd <= 0 or data.current_injection_rate <= 0:
            return 0.0

        volume_liters = data.current_injection_rate * LITERS_PER_GALLON
        mass_kg = volume_liters * self.settings.chemical_density
        gross_mass_lbs = mass_kg * KG_TO_LBS
        pure_mass_lbs = gross_mass_lbs * (self.settings.active_intensity / 100)
        water_mass_lbs = water_bpd * WATER_LBS_PER_BBL

        return (pure_mass_lbs / water_mass_lbs) * PPM_DIVISOR if water_mass_lbs > 0 else 0.0

    def optimize(self, data: ProductionData, previous_rate: Optional[float] = None) -> OptimizationResult:
        """Main optimization pipeline."""
        is_valid, validation_error = self.validate_and_filter(data, previous_rate)

        if not data.pump_status or data.gross_fluid_rate <= 0:
            return OptimizationResult(
                timestamp=data.timestamp,
                recommended_rate_gpd=0.0,
                actual_rate_gpd=data.current_injection_rate,
                savings_opportunity_usd=data.current_injection_rate * self.settings.cost_per_gallon,
                status_flag=StatusFlag.PUMP_OFF.value,
                water_bpd=0.0,
                current_ppm=0.0,
                target_ppm=self.settings.target_ppm
            )

        if not is_valid:
            return OptimizationResult(
                timestamp=data.timestamp,
                recommended_rate_gpd=None,
                actual_rate_gpd=data.current_injection_rate,
                savings_opportunity_usd=None,
                status_flag=StatusFlag.ERROR.value if validation_error == "SPIKE_DETECTED" else StatusFlag.NO_DATA.value,
                water_bpd=None,
                current_ppm=None,
                target_ppm=self.settings.target_ppm
            )

        water_bpd = self.calculate_water_volume(data)
        raw_recommended_gpd = self.calculate_required_chemical_volume(water_bpd)
        recommended_gpd = self.apply_constraints(raw_recommended_gpd)
        savings_opportunity = self.calculate_financial_impact(data.current_injection_rate, recommended_gpd)
        current_ppm = self.calculate_current_ppm(data, water_bpd)
        status = self.determine_status(data, recommended_gpd)

        return OptimizationResult(
            timestamp=data.timestamp,
            recommended_rate_gpd=recommended_gpd,
            actual_rate_gpd=data.current_injection_rate,
            savings_opportunity_usd=savings_opportunity,
            status_flag=status,
            water_bpd=water_bpd,
            current_ppm=current_ppm,
            target_ppm=self.settings.target_ppm
        )


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def get_well_settings(api: Api, asset_id: int) -> WellSettings:
    """Retrieve well settings from Corva database."""
    try:
        settings_data = api.get_dataset(
            provider="prabhat",
            dataset="chemical.saver.settings",
            query={"asset_id": asset_id},
            limit=1
        )
        if settings_data and len(settings_data) > 0:
            return WellSettings.from_database(settings_data[0].get('data', settings_data[0]))
    except Exception as e:
        Logger.warning(f"Failed to retrieve settings: {e}")

    return WellSettings.from_database(None)


def save_optimization_result(api: Api, asset_id: int, result: OptimizationResult) -> bool:
    """Save optimization result to Corva database."""
    try:
        api.post_dataset(
            provider="prabhat",
            dataset="chemical.optimization.results",
            data=[{
                "asset_id": asset_id,
                "version": 1,
                "timestamp": result.timestamp,
                "data": result.to_dict()
            }]
        )
        return True
    except Exception as e:
        Logger.error(f"Failed to save result: {e}")
        return False


def get_previous_flow_rate(cache: Cache, asset_id: int) -> Optional[float]:
    """Get previous flow rate from cache."""
    try:
        cached = cache.get(f"prev_flow_{asset_id}")
        return float(cached) if cached else None
    except Exception:
        return None


def set_previous_flow_rate(cache: Cache, asset_id: int, rate: float) -> None:
    """Store current flow rate in cache."""
    try:
        cache.set(f"prev_flow_{asset_id}", str(rate), ttl=600)
    except Exception as e:
        Logger.warning(f"Failed to cache: {e}")


# =============================================================================
# CORVA STREAM HANDLER (Main Entry Point)
# =============================================================================

@stream
def lambda_handler(event: StreamTimeEvent, api: Api, cache: Cache) -> None:
    """
    Corva stream handler - processes real-time production data
    and outputs chemical optimization results.
    """
    asset_id = event.asset_id
    records = event.records

    Logger.info(f"Processing {len(records)} records for asset {asset_id}")

    # Get well settings
    settings = get_well_settings(api, asset_id)

    # Initialize optimizer
    optimizer = ChemicalOptimizer(settings)

    # Get previous flow rate for spike detection
    previous_rate = get_previous_flow_rate(cache, asset_id)

    # Process records
    last_valid_water_cut = 50.0

    for record in records:
        data = ProductionData.from_record(record, last_valid_water_cut)
        result = optimizer.optimize(data, previous_rate)

        # Save result to database
        save_optimization_result(api, asset_id, result)

        # Update tracking
        previous_rate = data.gross_fluid_rate
        if 0 <= data.water_cut <= 100:
            last_valid_water_cut = data.water_cut

    # Cache for next run
    if previous_rate is not None:
        set_previous_flow_rate(cache, asset_id, previous_rate)

    Logger.info(f"Completed processing for asset {asset_id}")
