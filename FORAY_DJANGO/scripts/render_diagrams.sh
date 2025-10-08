#!/usr/bin/env bash
set -euo pipefail

FORCE=${FORCE:-0}
SPECIFIED_FILES=()

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--force] [file1.mmd] [file2.mmd] ...

Renders Mermaid diagrams from docs/diagrams/*.mmd to PNG and SVG formats 
in docs/diagrams/exports/{png,svg}/ with automatic complexity detection.
Complex diagrams with many nodes, subgraphs, or connections are rendered at higher resolution.

Input:  docs/diagrams/*.mmd (or specified files)
Output: docs/diagrams/exports/png/*.png
        docs/diagrams/exports/svg/*.svg

Options:
  --force     Re-render all diagrams even if output files are up-to-date (or set FORCE=1)
  -h, --help  Show this help
  
Arguments:
  file1.mmd   Specific diagram files to render (relative to docs/diagrams/)
  file2.mmd   Can specify multiple files, or omit to render all *.mmd files

Environment Variables:
  WIDTH                       Standard diagram width (default: 3200)
  HEIGHT                      Standard diagram height (default: 2400)
  HIGH_RES_WIDTH              High resolution width for complex diagrams (default: 4800)
  HIGH_RES_HEIGHT             High resolution height for complex diagrams (default: 3600)
  OUTPUT_FORMATS              Space-separated output formats (default: "png svg")
  DEBUG                       Show complexity detection details (set to 1)
  FORCE                       Force re-render all (set to 1)
  
Complexity Detection Thresholds:
  COMPLEXITY_LINE_THRESHOLD   Lines of code threshold (default: 80)
  COMPLEXITY_NODE_THRESHOLD   Number of nodes threshold (default: 25)
  COMPLEXITY_SUBGRAPH_THRESHOLD Number of subgraphs threshold (default: 5)

Examples:
  # Render all diagrams with debug output
  DEBUG=1 $(basename "$0")
  
  # Render specific diagrams
  $(basename "$0") matching_pipeline_flow.mmd best_match_algorithm_detail.mmd
  
  # Force render specific diagram
  $(basename "$0") --force matching_sequence_diagram.mmd
  
  # Generate only PNG files for all diagrams
  OUTPUT_FORMATS="png" $(basename "$0") --force
  
  # Generate only SVG files for specific diagram
  OUTPUT_FORMATS="svg" $(basename "$0") --force matching_system_architecture.mmd
  
  # Use custom high resolution for very complex diagrams
  HIGH_RES_WIDTH=6400 HIGH_RES_HEIGHT=4800 $(basename "$0") --force
  
  # Adjust complexity thresholds for smaller diagrams
  COMPLEXITY_LINE_THRESHOLD=50 $(basename "$0")

Diagram Files Available:
  - matching_pipeline_flow.mmd       # Complete pipeline process flow
  - matching_system_architecture.mmd # High-level system architecture
  - matching_sequence_diagram.mmd    # Detailed execution sequence
  - best_match_algorithm_detail.mmd  # Core algorithm deep dive
  - matching_performance_architecture.mmd # Performance characteristics
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --force)
      FORCE=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *.mmd)
      # Add file to list of specified files
      SPECIFIED_FILES+=("$1")
      ;;
    *)
      # Check if it's a file without .mmd extension
      if [ -f "docs/diagrams/$1.mmd" ]; then
        SPECIFIED_FILES+=("$1.mmd")
      elif [ -f "docs/diagrams/$1" ]; then
        SPECIFIED_FILES+=("$1")
      else
        echo "Error: File not found: $1" >&2
        echo "Looking for: docs/diagrams/$1 or docs/diagrams/$1.mmd" >&2
        echo "Available diagrams:"
        ls -1 docs/diagrams/*.mmd 2>/dev/null | sed 's|.*/||' || echo "  No diagrams found"
        exit 2
      fi
      ;;
  esac
  shift
done

WIDTH=${WIDTH:-3200}
HEIGHT=${HEIGHT:-2400}
OUTPUT_FORMATS=${OUTPUT_FORMATS:-"png svg"}

# High-resolution settings for complex diagrams
HIGH_RES_WIDTH=${HIGH_RES_WIDTH:-4800}
HIGH_RES_HEIGHT=${HIGH_RES_HEIGHT:-3600}

# Thresholds for detecting complex diagrams
COMPLEXITY_LINE_THRESHOLD=${COMPLEXITY_LINE_THRESHOLD:-80}
COMPLEXITY_NODE_THRESHOLD=${COMPLEXITY_NODE_THRESHOLD:-25}
COMPLEXITY_SUBGRAPH_THRESHOLD=${COMPLEXITY_SUBGRAPH_THRESHOLD:-5}

# Function to analyze diagram complexity
analyze_complexity() {
  local file="$1"
  local line_count node_count subgraph_count
  
  line_count=$(wc -l < "$file")
  node_count=$(grep -c -E '^\s*[A-Za-z0-9_]+\[|^\s*[A-Za-z0-9_]+\(' "$file" 2>/dev/null)
  node_count=${node_count:-0}
  subgraph_count=$(grep -c -E '^\s*subgraph' "$file" 2>/dev/null)
  subgraph_count=${subgraph_count:-0}
  
  if [ ${DEBUG:-0} -eq 1 ]; then
    echo "    Complexity analysis: lines=$line_count, nodes=$node_count, subgraphs=$subgraph_count"
  fi
  
  # Return 1 if complex, 0 if simple
  if [ "$line_count" -gt "$COMPLEXITY_LINE_THRESHOLD" ] || 
     [ "$node_count" -gt "$COMPLEXITY_NODE_THRESHOLD" ] || 
     [ "$subgraph_count" -gt "$COMPLEXITY_SUBGRAPH_THRESHOLD" ]; then
    return 1
  else
    return 0
  fi
}

# Check for Mermaid CLI availability
if command -v npx >/dev/null 2>&1; then
  RENDER_CMD="npx -y @mermaid-js/mermaid-cli"
elif command -v mmdc >/dev/null 2>&1; then
  RENDER_CMD="mmdc"
elif command -v docker >/dev/null 2>&1; then
  echo "Using Docker fallback for Mermaid rendering..."
  RENDER_CMD="docker run --rm -v $(pwd):/data minlag/mermaid-cli"
else
  echo "❌ Mermaid CLI not available. Install with:" >&2
  echo "  npm install -g @mermaid-js/mermaid-cli" >&2
  echo "  OR use Docker: docker pull minlag/mermaid-cli" >&2
  echo "  OR install mmdc locally" >&2
  exit 1
fi

# Ensure export directories exist
for format in $OUTPUT_FORMATS; do
  mkdir -p "docs/diagrams/exports/$format"
done

# Determine which files to process
if [ ${#SPECIFIED_FILES[@]} -gt 0 ]; then
  # Process specified files
  files=()
  for file in "${SPECIFIED_FILES[@]}"; do
    input_file="docs/diagrams/$file"
    if [ ! -f "$input_file" ]; then
      echo "❌ Diagram not found: $input_file" >&2
      exit 1
    fi
    files+=("$input_file")
  done
else
  # Process all .mmd files in the source directory
  files=(docs/diagrams/*.mmd)
fi

if [ ${#files[@]} -eq 0 ]; then
  echo "ℹ️  No Mermaid source files found in docs/diagrams/" >&2
  echo "Create .mmd files in docs/diagrams/ to get started" >&2
  exit 0
fi

echo "🍄 ForayNL Django Diagram Renderer"
echo "📁 Source: docs/diagrams/"

if [ ${DEBUG:-0} -eq 1 ]; then
  echo "Debug mode enabled"
  echo "Settings:"
  echo "  Standard resolution: ${WIDTH}x${HEIGHT}"
  echo "  High resolution: ${HIGH_RES_WIDTH}x${HIGH_RES_HEIGHT}"
  echo "  Output formats: $OUTPUT_FORMATS"
  echo "  Complexity thresholds: lines>$COMPLEXITY_LINE_THRESHOLD, nodes>$COMPLEXITY_NODE_THRESHOLD, subgraphs>$COMPLEXITY_SUBGRAPH_THRESHOLD"
fi

echo "🔧 Renderer: $RENDER_CMD"
if [ ${FORCE:-0} -eq 1 ]; then
  echo "🔁 Force mode: enabled"
fi
echo

rendered=0
skipped=0
errors=0

for input_file in "${files[@]}"; do
  base_name=$(basename "$input_file" .mmd)
  
  echo "🎨 Processing: $base_name"
  
  # Determine complexity and resolution
  use_width=""
  use_height=""
  complexity_suffix=""
  if analyze_complexity "$input_file"; then
    use_width=$WIDTH
    use_height=$HEIGHT
    complexity_suffix=" (standard resolution)"
    if [ ${DEBUG:-0} -eq 1 ]; then
      echo "    Using standard resolution: ${use_width}x${use_height}"
    fi
  else
    use_width=$HIGH_RES_WIDTH
    use_height=$HIGH_RES_HEIGHT
    complexity_suffix=" (high resolution - complex diagram)"
    echo "    📊 Complex diagram detected - using high resolution: ${use_width}x${use_height}"
  fi
  
  # Check which formats to render
  formats_array=($OUTPUT_FORMATS)
  need_render=0
  files_to_render=()
  
  for format in "${formats_array[@]}"; do
    case "$format" in
      png)
        output_file="docs/diagrams/exports/png/$base_name.png"
        if [ ${FORCE:-0} -eq 1 ] || [ ! -f "$output_file" ] || [ "$input_file" -nt "$output_file" ]; then
          files_to_render+=("png:$output_file:$use_width:$use_height")
          need_render=1
        fi
        ;;
      svg)
        output_file="docs/diagrams/exports/svg/$base_name.svg"
        if [ ${FORCE:-0} -eq 1 ] || [ ! -f "$output_file" ] || [ "$input_file" -nt "$output_file" ]; then
          files_to_render+=("svg:$output_file:::")
          need_render=1
        fi
        ;;
      *)
        echo "    ⚠️  Unknown format '$format', skipping"
        ;;
    esac
  done
  
  if [ "$need_render" -eq 0 ]; then
    echo "  ⏭️  Skipping (up to date)$complexity_suffix"
    ((skipped+=1))
    continue
  fi
  
  # Render each required format
  format_errors=0
  for render_spec in "${files_to_render[@]}"; do
    IFS=':' read -r format output_file width height <<< "$render_spec"
    
    echo "  🖼️  Generating $format..."
    
    # Build mermaid-cli command
    if [ "$format" = "png" ]; then
      cmd="$RENDER_CMD -i $input_file -o $output_file -w $width -H $height"
    else
      cmd="$RENDER_CMD -i $input_file -o $output_file"
    fi
    
    # Add puppeteer config if available
    if [ -f "scripts/puppeteer-config.json" ]; then
      cmd="$cmd --puppeteerConfigFile scripts/puppeteer-config.json"
    fi
    
    # Execute command
    if eval "$cmd" 2>/dev/null; then
      echo "    ✅ $format generated successfully$complexity_suffix"
    else
      echo "    ❌ $format generation failed" >&2
      ((format_errors+=1))
    fi
  done
  
  if [ "$format_errors" -eq 0 ]; then
    ((rendered+=1))
  else
    ((errors+=1))
  fi
  echo

done

echo
echo "🏁 Render complete!"
echo "  📊 Rendered: $rendered diagrams"
echo "  ⏭️  Skipped: $skipped (up-to-date)"
if [ $errors -gt 0 ]; then
  echo "  ❌ Errors: $errors"
  exit 1
else
  echo "  ✨ All diagrams processed successfully"
fi