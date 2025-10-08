# 🍄 ForayNL Fungi Matching Pipeline Documentation

## Overview

The ForayNL matching pipeline is a sophisticated fuzzy string matching system that correlates field observations of fungi with the authoritative MycoBank taxonomic database. It processes CSV data to identify perfect matches, categorize mismatches, and find the best taxonomic candidates using optimized algorithms and parallel processing.

## System Architecture

### Core Purpose
- **Primary Goal**: Match foray fungi observations against MycoBank taxonomic records
- **Data Sources**: Field observation CSV (983 records) + MycoBank database CSV (537k+ records)
- **Output**: Categorized matches with similarity scores and explanations
- **Performance Target**: Process ~527M potential comparisons efficiently using algorithmic optimization

## Data Flow Architecture

### Input Processing Pipeline
1. **File Loading**: CSV files with specific encoding (`latin-1`) and column selection
2. **Data Normalization**: String cleaning, null handling, column mapping
3. **Index Construction**: First-letter bucketing for algorithmic efficiency
4. **Parallel Processing**: Multi-threaded matching with shared executor
5. **Result Categorization**: Four distinct output types with specific purposes

### Output Data Models
The pipeline generates four categories of results:

#### 1. ForayPerfectMatch
- **Condition**: All three name variants identical (`a == b == c`)
- **Purpose**: High-confidence identity matches
- **Fields**: `foray_id`, `name`
- **Volume**: Typically <5% of total records

#### 2. ForayMismatchExplanation  
- **Condition**: Name variants differ in some way
- **Categories**:
  - `ORG_CONF_MATCH`: Original and conference names match
  - `ORG_FORAY_MATCH`: Original and foray names match
  - `CONF_FORAY_MATCH`: Conference and foray names match
  - `ALL_DIFFERENT`: All three names unique
- **Fields**: `foray_id`, `org_entry`, `conf_name`, `foray_name`, `explanation`

#### 3. ForayPerfectMycoMatch
- **Condition**: Perfect foray match + exact MycoBank hit (score=100)
- **Purpose**: Definitive taxonomic identification
- **Fields**: `foray_id`, `mycobank_id`, `mycobank_name`
- **Volume**: Subset of perfect matches with exact database hits

#### 4. ForayMismatchMycoScores
- **Condition**: Mismatched names with MycoBank candidate analysis
- **Purpose**: Best-guess taxonomic assignments with confidence scores
- **Fields**: `foray_id`, `org_score`, `conf_score`, `foray_score`, `mycobank_id`, `mycobank_name`, `mycobank_expl`
- **Selection**: Single best candidate chosen from three parallel searches

## Core Functions Deep Dive

### Data Processing Functions

#### `_norm(s: str) -> str`
```python
def _norm(s: str) -> str:
    return (s or "").strip()
```
- **Purpose**: Safe string normalization handling None/null values
- **Usage**: Universal string preprocessing throughout pipeline
- **Importance**: Prevents downstream errors from dirty data

#### `_preferred_name(taxon_name: str, current_name: str) -> str`
```python
def _preferred_name(taxon_name: str, current_name: str) -> str:
    return _norm(current_name) or _norm(taxon_name)
```
- **Business Rule**: Current taxonomic names preferred over historical names
- **Rationale**: Reflects modern taxonomic consensus and nomenclature updates
- **Impact**: Affects matching accuracy and result interpretation

### Configuration Functions

#### `_choose_workers() -> int`
```python
def _choose_workers() -> int:
    override = os.getenv("PIPELINE_WORKERS")
    if override and override.isdigit():
        return max(1, int(override))
    cpu = os.cpu_count() or 4
    return min(16, max(4, cpu * 2))
```
- **Policy**: Environment override → calculated (2×CPU) → bounds [4,16]
- **Rationale**: Balance performance vs resource consumption
- **Tuning**: Optimized for RapidFuzz threading characteristics

#### `_env_truthy(name: str) -> bool`
```python
def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "y"}
```
- **Purpose**: Flexible boolean environment variable parsing
- **Usage**: Feature flags like `SKIP_SAVE_ORIGINALS`
- **Flexibility**: Supports multiple boolean representations

### Core Matching Algorithm

#### `best_match(query: str, source: str)`
The heart of the matching system with sophisticated optimization:

**Algorithm Flow:**
1. **Input Validation**: Check for empty queries
2. **First-Letter Indexing**: Reduce candidate pool from 537k to ~22k
3. **Parallel Scoring**: RapidFuzz ratio calculation against taxon_name and current_name
4. **Preference Logic**: Choose higher score between TAXON vs UPDATED matches
5. **Result Packaging**: Return best candidate with score and explanation

**Performance Optimizations:**
- **LRU Cache**: `@lru_cache(maxsize=100_000)` prevents re-computation
- **First-Letter Bucketing**: Massive algorithmic speedup (O(n) vs O(n²))
- **Thread Safety**: Pure function with immutable data structures
- **GIL Release**: RapidFuzz releases Python GIL for true parallelism

**Explanation Generation:**
- `"ORG → TAXON"`: Original entry matched taxonomic name
- `"ORG → UPDATED"`: Original entry matched current name
- `"CONF → TAXON"`: Conference name matched taxonomic name
- `"CONF → UPDATED"`: Conference name matched current name
- `"FORAY → TAXON"`: Foray name matched taxonomic name
- `"FORAY → UPDATED"`: Foray name matched current name

### Pipeline Orchestration

#### `row_work(ex: ThreadPoolExecutor, fid: str, a: str, b: str, c: str)`
Processes individual foray records through the complete matching pipeline:

**Decision Tree Logic:**
1. **Perfect Match Detection**: `if a == b == c`
   - Create `ForayPerfectMatch` record
   - Attempt exact MycoBank lookup
   - Create `ForayPerfectMycoMatch` if exact hit found

2. **Mismatch Classification**: Categorize relationship between three names
   - Analyze which names match vs differ
   - Create `ForayMismatchExplanation` with category

3. **Candidate Search**: For mismatches only
   - Launch three parallel `best_match()` calls
   - Compare scores across all three name variants
   - Select single best candidate overall
   - Create `ForayMismatchMycoScores` with winner

**Parallel Execution Pattern:**
```python
f_org = ex.submit(best_match, a, "ORG")
f_conf = ex.submit(best_match, b, "CONF")  
f_foray = ex.submit(best_match, c, "FORAY")
# Collect results and choose best
```

## Data Structure Design

### MycoBank Indexing Structure
```python
grouped_candidates: dict[str, list[tuple[str, str, dict]]]
```

**Structure Breakdown:**
- **Key**: First letter of preferred name (uppercase)
- **Value**: List of tuples containing:
  - `taxon_name`: Historical/original taxonomic name
  - `current_name`: Modern accepted taxonomic name  
  - `row_dict`: Complete record data (ID, authors, year, hyperlink)

**Performance Impact:**
- **Dramatic Speedup**: 537k records → ~22k candidates per query
- **Memory Efficiency**: Single shared index across all queries
- **Cache Friendly**: Repeated queries benefit from bucket locality

**Example Structure:**
```python
{
    'A': [('Agaricus campestris', 'Agaricus campestris', {...}), ...],
    'B': [('Boletus edulis', 'Boletus edulis', {...}), ...],
    'C': [('Cantharellus cibarius', 'Cantharellus cibarius', {...}), ...],
    # ... for each letter
}
```

## Performance Characteristics

### Threading Strategy
- **Shared ThreadPoolExecutor**: Reduces overhead vs per-row executors
- **Optimal Worker Count**: Dynamic scaling based on CPU cores and limits
- **GIL Optimization**: RapidFuzz releases Python GIL for true parallelism
- **Work Distribution**: Each foray record processed independently

### Memory Management
- **Streaming Processing**: Results collected incrementally, not bulk-loaded
- **LRU Cache Bounds**: 100k entry limit prevents unbounded growth
- **Index Sharing**: Single candidate index shared across all threads
- **Garbage Collection**: Lists cleared and rebuilt for each batch

### Algorithmic Complexity
- **Brute Force**: O(n×m) = 983 × 537k = 527M comparisons
- **Optimized**: O(n×(m/26)) ≈ 983 × 22k = 21M comparisons  
- **Speedup**: ~25x improvement through first-letter indexing
- **Cache Hits**: Additional speedup for repeated queries

### Progress Reporting
```python
if i % 100 == 0 or i == total:
    elapsed = time.time() - start_time
    rate = i / elapsed if elapsed > 0 else 0
    remaining = (total - i) / rate if rate > 0 else 0
```

**Metrics Provided:**
- **Progress**: Current position and percentage complete
- **Performance**: Records processed per second
- **ETA**: Estimated time to completion
- **Results**: Running counts of perfect matches and mismatches
- **Timing**: Elapsed time for performance monitoring

## Error Handling & Robustness

### File System Protection
```python
if not os.path.exists(FORAY_PATH):
    raise FileNotFoundError(f"Missing Foray CSV: {FORAY_PATH}")
```
- **Fail Fast**: Immediate error if required files missing
- **Clear Messages**: Specific file paths in error messages
- **Preventive**: Catches issues before pandas processing

### Data Quality Protection
- **Null Handling**: `_norm()` function handles None values gracefully
- **Encoding**: Explicit `latin-1` encoding for CSV compatibility
- **Type Safety**: `dtype=str` prevents pandas type inference issues
- **Default Values**: `.fillna("")` ensures consistent string data

### Threading Safety
- **Pure Functions**: `best_match()` has no side effects
- **Immutable Data**: Candidate index built once, never modified
- **Thread-Local Storage**: Each thread works on independent data
- **Atomic Operations**: Database updates use Django ORM transactions

## Configuration & Customization

### Environment Variables
- **`PIPELINE_WORKERS`**: Override automatic worker count calculation
- **`SKIP_SAVE_ORIGINALS`**: Skip database persistence for speed (testing)

### File Paths
```python
FORAY_PATH = "data/2023ForayNL_Fungi.csv"
MYCOBANK_PATH = "data/MBList.csv"
```

### Column Mappings
**Foray CSV Columns:**
- `id` → `foray_id`
- `genus_and_species_org_entry` → original name variant
- `genus_and_species_conf` → conference name variant  
- `genus_and_species_foray_name` → foray name variant

**MycoBank CSV Columns:**
- `MycoBank #` → `mycobank_id`
- `Taxon name` → `taxon_name`
- `Current name.Taxon name` → `current_name`
- `Authors` → `authors`
- `Year of effective publication` → `year`
- `Hyperlink` → `hyperlink`

## Integration Points

### Database Models
The pipeline integrates with Django ORM models:
- **ForayFungi2023**: Original foray observations
- **MycoBankList**: MycoBank taxonomic database
- **ForayPerfectMatch**: Perfect name matches
- **ForayMismatchExplanation**: Mismatch categorizations
- **ForayPerfectMycoMatch**: Perfect matches with exact DB hits
- **ForayMismatchMycoScores**: Scored candidate matches

### Management Command Interface
```python
# Called from Django management command
perfect_list, mismatch_list, perfect_myco, mismatch_scores = run_pipeline()
```

### Admin Interface Integration
Results can be analyzed through enhanced Django admin filters:
- **Collection Series Filtering**: Group by foray collection events
- **Score Range Filtering**: Filter by confidence levels
- **Match Status Filtering**: Track pipeline results
- **Name Consistency Analysis**: Identify data quality issues

## Use Cases & Workflows

### Research Applications
1. **Species Identification**: Match field observations to accepted taxonomy
2. **Data Quality Assessment**: Identify naming inconsistencies in observations
3. **Taxonomic Validation**: Verify species names against authoritative database
4. **Historical Analysis**: Track taxonomic name changes over time

### Administrative Workflows
1. **Batch Processing**: Process entire foray datasets efficiently
2. **Quality Control**: Review low-confidence matches manually
3. **Database Maintenance**: Update observation records with validated names
4. **Export Generation**: Create reports for research publication

### Performance Monitoring
1. **Processing Speed**: Track records per second for optimization
2. **Match Quality**: Analyze distribution of similarity scores
3. **Resource Usage**: Monitor memory and CPU consumption
4. **Cache Efficiency**: Measure hit rates for optimization

## Future Enhancement Opportunities

### Algorithmic Improvements
- **Phonetic Matching**: Add Soundex/Metaphone for pronunciation-based matching
- **Fuzzy Indexing**: Use BK-trees or similar for sub-linear fuzzy search
- **Machine Learning**: Train models on validated matches for better scoring
- **Taxonomic Hierarchy**: Incorporate genus/family relationships

### Performance Optimizations
- **GPU Acceleration**: Use CUDA for massive parallel string matching
- **Distributed Processing**: Scale across multiple machines for huge datasets
- **Memory Mapping**: Use memory-mapped files for large reference databases
- **Incremental Processing**: Support delta updates vs full reprocessing

### Feature Enhancements
- **Interactive Matching**: Web interface for manual review and correction
- **Confidence Thresholds**: Configurable score cutoffs for auto-acceptance
- **Multi-Database Support**: Integrate additional taxonomic databases
- **Version Management**: Track changes in taxonomic names over time

---

This matching pipeline represents a production-ready solution for large-scale taxonomic name matching with excellent performance characteristics, robust error handling, and comprehensive result categorization suitable for scientific research workflows.