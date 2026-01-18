"""
Chemical Saver - Dosage Optimization Backend
Production API for Cloud Run

This module calculates optimal chemical injection rates based on real-time
production data and user-defined settings.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
WATER_LBS_PER_BBL = 350.0  # lbs per barrel of water
KG_TO_LBS = 2.20462
LITERS_PER_GALLON = 3.78541
PPM_DIVISOR = 1_000_000

# Safety thresholds
SPIKE_THRESHOLD_PERCENT = 500  # 500% change = likely sensor error
NO_DATA_TIMEOUT_SECONDS = 300  # 5 minutes
UNDER_DOSE_THRESHOLD_PERCENT = 10  # 10% under target = corrosion risk


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
        timestamp = record.get('timestamp', int(datetime.now().timestamp()))
        gross_fluid_rate = float(record.get('gross_fluid_rate', 0) or 0)

        # Water cut validation with forward fill
        water_cut = record.get('water_cut')
        if water_cut is None or not (0 <= water_cut <= 100):
            water_cut = last_valid_water_cut
        else:
            water_cut = float(water_cut)

        current_injection_rate = float(record.get('current_injection_rate', 0) or 0)

        # Derive pump status from flow rate
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
            'recommended_rate_gpd': round(self.recommended_rate_gpd, 3),
            'actual_rate_gpd': round(self.actual_rate_gpd, 3),
            'savings_opportunity_usd': round(self.savings_opportunity_usd, 2),
            'status_flag': self.status_flag,
            'water_bpd': round(self.water_bpd, 2),
            'current_ppm': round(self.current_ppm, 1),
            'target_ppm': self.target_ppm
        }


# =============================================================================
# CORE OPTIMIZATION LOGIC
# =============================================================================

class ChemicalOptimizer:
    """
    Core optimization engine for chemical dosage calculations.

    Implements the exact logic sequence:
    1. Data Validation & Cleaning
    2. Calculate Water Volume
    3. Calculate Required Chemical Volume
    4. Apply Constraints
    5. Calculate Financial Impact
    """

    def __init__(self, settings: WellSettings):
        self.settings = settings
        self._last_valid_water_cut = 50.0
        self._last_gross_fluid_rate = None
        self._last_data_timestamp = None

    def validate_and_filter(
        self,
        data: ProductionData,
        previous_rate: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Step 1: Data Validation & Cleaning

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for data staleness (no data for 5 minutes)
        if self._last_data_timestamp:
            time_diff = data.timestamp - self._last_data_timestamp
            if time_diff > NO_DATA_TIMEOUT_SECONDS:
                return False, "NO_DATA_TIMEOUT"

        # Spike filter: Check for 500% jump in 1 minute
        if previous_rate is not None and previous_rate > 0:
            change_percent = abs(data.gross_fluid_rate - previous_rate) / previous_rate * 100
            if change_percent > SPIKE_THRESHOLD_PERCENT:
                logger.warning(
                    f"Spike detected: {change_percent:.1f}% change in flow rate. "
                    f"Previous: {previous_rate}, Current: {data.gross_fluid_rate}"
                )
                return False, "SPIKE_DETECTED"

        # Update tracking
        self._last_data_timestamp = data.timestamp
        if 0 <= data.water_cut <= 100:
            self._last_valid_water_cut = data.water_cut

        return True, None

    def calculate_water_volume(self, data: ProductionData) -> float:
        """
        Step 2: Calculate Water Volume

        Formula: Water_BPD = Gross_Fluid_Rate * (Water_Cut / 100)
        """
        return data.gross_fluid_rate * (data.water_cut / 100)

    def calculate_required_chemical_volume(self, water_bpd: float) -> float:
        """
        Step 3: Calculate Required Chemical Volume (The Optimization)

        Process:
        1. Convert Water BPD to lbs/day
        2. Calculate Pure Chemical Mass needed
        3. Adjust for Intensity
        4. Convert Mass to Volume (Gallons)
        """
        if water_bpd <= 0:
            return 0.0

        # Convert Water BPD to lbs/day
        water_mass_lbs = water_bpd * WATER_LBS_PER_BBL

        # Calculate Pure Chemical Mass needed (in lbs)
        # Formula: Mass_Needed = Water_Mass * (Target_PPM / 1,000,000)
        pure_chemical_mass_lbs = water_mass_lbs * (self.settings.target_ppm / PPM_DIVISOR)

        # Adjust for Active Intensity
        # Formula: Gross_Mass_Needed = Mass_Needed / (Active_Intensity / 100)
        intensity_factor = self.settings.active_intensity / 100
        if intensity_factor <= 0:
            intensity_factor = 1.0  # Safety fallback
        gross_chemical_mass_lbs = pure_chemical_mass_lbs / intensity_factor

        # Convert Mass to Volume (Gallons)
        # First convert lbs to kg, then kg to liters using density, then to gallons
        gross_chemical_mass_kg = gross_chemical_mass_lbs / KG_TO_LBS
        volume_liters = gross_chemical_mass_kg / self.settings.chemical_density
        volume_gallons = volume_liters / LITERS_PER_GALLON

        return volume_gallons

    def apply_constraints(self, recommended_gpd: float) -> float:
        """
        Step 4: Apply Constraints

        Enforce min/max pump rate limits.
        """
        if recommended_gpd <= 0:
            return 0.0

        # Apply minimum constraint
        if recommended_gpd < self.settings.min_pump_rate:
            return self.settings.min_pump_rate

        # Apply maximum constraint
        if recommended_gpd > self.settings.max_pump_rate:
            return self.settings.max_pump_rate

        return recommended_gpd

    def calculate_financial_impact(
        self,
        current_rate: float,
        recommended_rate: float
    ) -> float:
        """
        Step 5: Calculate Financial Impact (The Audit)

        Formula: Daily_Waste_Cost = Delta_GPD * Cost_Per_Gallon

        Note: Positive = Over-injecting/Wasting money
              Negative = Under-injecting/Risking corrosion
        """
        delta_gpd = current_rate - recommended_rate
        return delta_gpd * self.settings.cost_per_gallon

    def determine_status(
        self,
        data: ProductionData,
        recommended_rate: float,
        validation_error: Optional[str] = None
    ) -> str:
        """Determine the status flag based on current state."""
        if validation_error:
            if validation_error == "NO_DATA_TIMEOUT":
                return StatusFlag.NO_DATA.value
            return StatusFlag.ERROR.value

        if not data.pump_status or data.gross_fluid_rate <= 0:
            return StatusFlag.PUMP_OFF.value

        if recommended_rate <= 0:
            return StatusFlag.PUMP_OFF.value

        # Calculate the difference percentage
        if recommended_rate > 0:
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

        # Reverse the calculation to get current PPM
        # Volume (gallons) -> Liters -> kg -> lbs
        volume_liters = data.current_injection_rate * LITERS_PER_GALLON
        mass_kg = volume_liters * self.settings.chemical_density
        gross_mass_lbs = mass_kg * KG_TO_LBS

        # Apply intensity to get pure chemical mass
        pure_mass_lbs = gross_mass_lbs * (self.settings.active_intensity / 100)

        # Calculate PPM
        water_mass_lbs = water_bpd * WATER_LBS_PER_BBL
        if water_mass_lbs <= 0:
            return 0.0

        current_ppm = (pure_mass_lbs / water_mass_lbs) * PPM_DIVISOR
        return current_ppm

    def optimize(
        self,
        data: ProductionData,
        previous_rate: Optional[float] = None
    ) -> OptimizationResult:
        """
        Main optimization pipeline - executes all steps in sequence.
        """
        # Step 1: Validate
        is_valid, validation_error = self.validate_and_filter(data, previous_rate)

        # Handle pump off condition
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

        # Handle validation errors (but don't return 0 for no-data)
        if not is_valid and validation_error == "NO_DATA_TIMEOUT":
            return OptimizationResult(
                timestamp=data.timestamp,
                recommended_rate_gpd=None,  # Null per requirements
                actual_rate_gpd=data.current_injection_rate,
                savings_opportunity_usd=None,
                status_flag=StatusFlag.NO_DATA.value,
                water_bpd=None,
                current_ppm=None,
                target_ppm=self.settings.target_ppm
            )

        # Handle spike - skip this data point but return last known good values
        if not is_valid and validation_error == "SPIKE_DETECTED":
            return OptimizationResult(
                timestamp=data.timestamp,
                recommended_rate_gpd=None,
                actual_rate_gpd=data.current_injection_rate,
                savings_opportunity_usd=None,
                status_flag=StatusFlag.ERROR.value,
                water_bpd=None,
                current_ppm=None,
                target_ppm=self.settings.target_ppm
            )

        # Step 2: Calculate Water Volume
        water_bpd = self.calculate_water_volume(data)

        # Step 3: Calculate Required Chemical Volume
        raw_recommended_gpd = self.calculate_required_chemical_volume(water_bpd)

        # Step 4: Apply Constraints
        recommended_gpd = self.apply_constraints(raw_recommended_gpd)

        # Step 5: Calculate Financial Impact
        savings_opportunity = self.calculate_financial_impact(
            data.current_injection_rate,
            recommended_gpd
        )

        # Calculate current PPM for display
        current_ppm = self.calculate_current_ppm(data, water_bpd)

        # Determine status
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

def get_well_settings(api: Any, asset_id: int) -> WellSettings:
    """Retrieve well settings from Corva database."""
    try:
        settings_data = api.get_dataset(
            provider="custom",
            collection="chemical.saver.settings",
            asset_id=asset_id,
            limit=1
        )

        if settings_data and len(settings_data) > 0:
            return WellSettings.from_database(settings_data[0])

    except Exception as e:
        logger.warning(f"Failed to retrieve settings for asset {asset_id}: {e}")

    # Return defaults if no settings found
    return WellSettings.from_database(None)


def save_optimization_result(api: Any, asset_id: int, result: OptimizationResult) -> bool:
    """Save optimization result to Corva database."""
    try:
        api.post_dataset(
            provider="custom",
            collection="chemical.optimization.results",
            asset_id=asset_id,
            data=[result.to_dict()]
        )
        return True
    except Exception as e:
        logger.error(f"Failed to save result for asset {asset_id}: {e}")
        return False


def get_previous_flow_rate(cache: Any, asset_id: int) -> Optional[float]:
    """Get previous flow rate from cache for spike detection."""
    try:
        cached = cache.get(f"prev_flow_{asset_id}")
        return float(cached) if cached else None
    except Exception:
        return None


def set_previous_flow_rate(cache: Any, asset_id: int, rate: float) -> None:
    """Store current flow rate in cache for next iteration."""
    try:
        cache.set(f"prev_flow_{asset_id}", str(rate), ttl=600)  # 10 min TTL
    except Exception as e:
        logger.warning(f"Failed to cache flow rate: {e}")


# =============================================================================
# LAMBDA HANDLER (Corva Entry Point)
# =============================================================================

def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Main entry point for Corva stream app.

    Processes incoming production data and outputs optimization results.
    """
    # For Corva SDK v2+, use the @stream decorator pattern
    # This handler supports both direct invocation and SDK patterns

    try:
        # Parse event data
        records = event.get('records', [])
        asset_id = event.get('asset_id')

        if not records:
            logger.info("No records to process")
            return {'status': 'success', 'processed': 0}

        # Initialize API and Cache (Corva SDK provides these)
        api = event.get('api')
        cache = event.get('cache')

        # Get well settings
        settings = get_well_settings(api, asset_id) if api else WellSettings.from_database(None)

        # Initialize optimizer
        optimizer = ChemicalOptimizer(settings)

        # Get previous flow rate for spike detection
        previous_rate = get_previous_flow_rate(cache, asset_id) if cache else None

        # Process each record
        results = []
        last_valid_water_cut = 50.0

        for record in records:
            # Parse production data
            data = ProductionData.from_record(record, last_valid_water_cut)

            # Run optimization
            result = optimizer.optimize(data, previous_rate)
            results.append(result)

            # Update tracking
            previous_rate = data.gross_fluid_rate
            if 0 <= data.water_cut <= 100:
                last_valid_water_cut = data.water_cut

        # Save results to database
        if api and results:
            for result in results:
                save_optimization_result(api, asset_id, result)

        # Cache last flow rate for next invocation
        if cache and previous_rate is not None:
            set_previous_flow_rate(cache, asset_id, previous_rate)

        logger.info(f"Processed {len(results)} records for asset {asset_id}")

        return {
            'status': 'success',
            'processed': len(results),
            'results': [r.to_dict() for r in results]
        }

    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


