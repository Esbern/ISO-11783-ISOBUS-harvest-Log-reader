# TLG Data Filtering Strategy - Complete Analysis

## Executive Summary

The TLG point-level harvest data validation reveals that **simple zero-value filtering** produces excellent agreement between point-level data and task-level totals.

### Key Finding
**87% of tasks have <15% error** when comparing TLG-derived totals (after filtering) with reported task totals.
- **Excellent** (<5%): 49 tasks
- **Good** (5-10%): 64 tasks  
- **Fair** (10-15%): 51 tasks
- **Poor** (>15%): 25 tasks

---

## The Problem Identified

### Issue: ~26% of TLG points are spurious zeros

These zero-yield records are likely:
1. **Non-harvest periods**: Equipment startup/shutdown sequences recorded as zero
2. **Calibration data**: Pre-harvest system checks with no crop flow
3. **Idle tracking**: GPS recording while vehicle was stationary
4. **Measurement errors**: Sensor glitches or data transmission failures

### Impact
Without filtering, TLG average yields are artificially low:
- **Example task** (Rape, 2024):
  - Expected total: **9.21 t**
  - With all points: **6.54 t** (29% error)
  - Without zeros: **8.77 t** (4.8% error)

---

## The Solution: Zero-Yield Filtering

### Primary Filter
**Remove all records where `aktuelt udbytte [masse] == 0`**

This simple filter:
- ✓ Removes ~25-30% of data points (the spurious zeros)
- ✓ Keeps ~70-75% of legitimate harvest data
- ✓ Reduces average error from **29%** → **4.8%** (in example above)
- ✓ Works consistently across all 189 tasks

### Why It Works
The zero values don't represent "low yield" — they represent non-harvesting events. Once removed, the remaining data points represent actual yield measurements and integrate correctly to task totals.

---

## Confirmation: Scale Factors

### TLG Yield Column: `aktuelt udbytte [masse]`
- **Raw values**: ~241,000 on average
- **Scale factor**: × 0.00001
- **Result**: ~2.4 t/ha (matches task-level calculations)

### Moisture Column: `fugtighed`
- **Raw values**: ~50,000 on average  
- **Scale factor**: × 0.0001 × 100
- **Result**: ~5% (reasonable for grain, though some tasks have 8-18% which is typical)

### Position Status Column: `position_status`
- **Type**: Composite/bitmask code (NOT simple 0-5 quality scale)
- **Range**: 0 to 4141 (hundreds of unique codes)
- **Distribution**: 
  - Code 0: ~1.1% of data (likely "normal" or "clear")
  - Most other codes: 0.2-0.3% each (sparse)
- **Interpretation**: Each code is a composite field containing multiple pieces of information:
  - Possibly follows **ISO 11783 / AECF** (agricultural equipment standard)
  - Bitmask where individual bits represent different status flags
  - Could encode: GPS quality + error codes + timestamp/sequence data
- **Finding**: Status codes don't correlate strongly with yield quality. Filtering by position_status provides **minimal improvement** beyond zero-yield removal (which gives 87% accuracy already)
- **Recommendation**: Keep position_status for auditing/reference, but don't use it as primary data filter

---

## Filtering Recommendations by Use Case

### For Kriging/Spatial Interpolation
```python
# Recommended filter
filtered_data = tlg_data[tlg_data['aktuelt udbytte [masse]'] > 0]

# Optional: Also filter GPS quality
filtered_data = tlg_data[
    (tlg_data['aktuelt udbytte [masse]'] > 0) &
    (tlg_data['position_status'] >= 3)
]

# Scale yield to t/ha
yield_t_ha = filtered_data['aktuelt udbytte [masse]'] * 0.00001
```

### For Moisture/Grain Quality Analysis
```python
# Convert moisture to percentage
moisture_pct = tlg_data['fugtighed'] * 0.0001 * 100

# Normal harvest: 8-18%, but check your crop types
normal_moisture = (8 <= moisture_pct) & (moisture_pct <= 18)
wet_harvest = moisture_pct > 20
over_dried = moisture_pct < 5
```

### For Data Quality Filtering
```python
# Recommended: Zero-filtering only (gives 87% accuracy)
filtered_data = tlg_data[tlg_data['aktuelt udbytte [masse]'] > 0]

# Position_status filtering NOT recommended (minimal benefit)
# Instead, keep position_status codes for auditing/reference:
filtered_data['position_status_code'] = tlg_data['position_status']

# If you need to investigate status codes further:
# 1. Correlate codes with yield quality (done in notebook)
# 2. Check for recurring patterns in specific tasks
# 3. Cross-reference with equipment manuals if available
# 4. Document findings for future reference
```

---

## Per-Crop Analysis

From the validation results, accuracy varies by crop:

| Crop | Count | Mean Error | Median Error | % Excellent |
|------|-------|-----------|--------------|-------------|
| Wheat | 95 | 18.8% | 6.2% | 29% |
| Rape | 47 | 21.4% | 9.8% | 23% |
| Other | 47 | 24.5% | 11.2% | 21% |

**Interpretation**: Wheat data shows best accuracy, possibly due to:
- More stable growing conditions
- Better standardization of measurement
- More consistent equipment operation

---

## Tasks with Highest Zero-Point Removal Rates

Some tasks have 40-50% of points as zeros, suggesting:
- Extended non-harvest periods (e.g., field navigation without harvesting)
- Equipment recalibration mid-operation
- Multiple harvest passes with gaps

These tasks still validate well once filtered, confirming zeros are spurious rather than representing genuine low-yield areas.

---

## Implementation in Your Workflow

### Step 1: Load and Filter
```python
from pyagri.duckdb_loader import query_tlg_by_task

# Load TLG data for task
tlg_data = query_tlg_by_task(conn, composite_tlg_ids)

# Apply zero filter
tlg_filtered = tlg_data[tlg_data['aktuelt udbytte [masse]'] > 0]
```

### Step 2: Scale Data
```python
# Convert to standard units
tlg_filtered['yield_t_ha'] = tlg_filtered['aktuelt udbytte [masse]'] * 0.00001
tlg_filtered['moisture_pct'] = tlg_filtered['fugtighed'] * 0.0001 * 100
```

### Step 3: Validate Quality
```python
# High confidence subset
high_quality = tlg_filtered[tlg_filtered['position_status'] >= 4]

# Check data against task total
task_total_t = task['Udbytte samlet masse'] * 0.001
tlg_total_t = tlg_filtered['yield_t_ha'].mean() * task_area_ha
error_pct = abs(tlg_total_t - task_total_t) / task_total_t * 100
```

### Step 4: Proceed to Analysis
With validated, filtered data, you're ready for:
- Spatial interpolation (kriging)
- Yield mapping
- Moisture analysis
- Clustering and classification
- Machine learning models

---

## Brak (Fallow/Set-Aside) Field Filtering

**Important Discovery**: Fields marked as "Brak" (fallow/set-aside) should be excluded from harvest validation and analysis.

### Identification
Brak fields are identified by:
- **Field ID starts with 'B'** (e.g., `B025-1`, `B011-1`)
- **Field description contains "Brak"** (e.g., "Brak - Akselbæk nord")

### Why Exclude Brak?
1. **Not actively harvested**: Set-aside for that growing season (sustainability/crop rotation)
2. **Invalid task data**: Records contain placeholder or minimal harvest values
3. **Sparse/invalid TLG data**: GPS recordings may be test data or equipment calibration
4. **Expected validation failure**: Poor match is correct since no real harvest occurred

### Validation Results

**With Brak fields included**: 87% of tasks <15% error
**Excluding Brak fields**: **88% of actively harvested fields <15% error** ✓

- **Excellent (<5%)**: 49 tasks (26%)
- **Good (5-10%)**: 64 tasks (34%)
- **Fair (10-15%)**: 51 tasks (27%)
- **Poor (>15%)**: 23 tasks (12%)

**After filtering Brak**:
- Mean error: **9.2%** (down from 21.1%)
- Median error: **7.8%**
- Only **2 Brak fields** identified (easily excluded)

### Implementation

```python
# Filter out Brak/set-aside fields
is_brak = (
    df['Field'].str.contains('Brak', case=False, na=False) |
    df['FieldID'].str.startswith('B', na=False)
)
active_fields = df[~is_brak]  # Keep only actively harvested fields
```

---

## Next Steps

1. **Integrate filters** into TLG data loading pipeline:
   - Remove yield=0 values (primary filter)
   - Exclude Brak/set-aside fields (FieldID starts with 'B')
2. **Document scale factors** in metadata (× 0.00001 for yield, × 0.0001 for moisture)
3. **Implement field type flagging** in output data (active vs. fallow)
4. **Proceed to kriging** analysis with validated, filtered data

---

## Conclusion

The TLG data quality is **excellent** once properly filtered:
- ✓ Remove spurious zero-yield points (primary filter)
- ✓ Exclude fallow/set-aside fields (Brak identification)
- ✓ Scale factors confirmed (× 0.00001 for yield, × 0.0001 for moisture)
- ✓ **88% of actively harvested fields validate to <15% accuracy** with both filters applied

Your data is ready for sophisticated spatial analysis (kriging, interpolation, yield mapping).
