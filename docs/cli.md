# Command-Line Interface

## Installation Check

Verify PiDraw is installed and available:

```bash
pidraw version
```

Expected output: `pidraw v0.1.0`

## Global Options

These options are available on every command:

| Option | Short | Description |
|--------|-------|-------------|
| `--quiet` | `-q` | Suppress non-essential output |
| `--verbose` | `-v` | Show detailed output |
| `--debug` | `-d` | Show debug messages |

## Commands

### pidraw render

Render a diagram file to SVG.

**Usage:**

```bash
pidraw render <file> [--output <path>] [--language <lang>] [--optimize]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output SVG file path (default: stdout) |
| `--language` | `-l` | Explicit diagram language (skip auto-detect) |
| `--optimize` | `-O` | Optimise the output SVG |

**Examples:**

```bash
pidraw render diagram.mmd
pidraw render diagram.mmd -o output.svg
pidraw render diagram.dot -l graphviz -O
pidraw render input.puml -o diagram.svg -O -v
```

---

### pidraw detect

Detect the diagram language used in a file.

**Usage:**

```bash
pidraw detect <file>
```

**Examples:**

```bash
pidraw detect diagram.mmd
pidraw detect source.unknown -v
```

---

### pidraw analyze

Run full diagnostics on a diagram file: language detection, renderer check, rendering, and optimization metrics.

**Usage:**

```bash
pidraw analyze <file> [--no-render] [--no-optimize]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--render / --no-render` | Run the renderer (default: True) |
| `--optimize / --no-optimize` | Optimise the output (default: True) |

**Examples:**

```bash
pidraw analyze diagram.mmd
pidraw analyze diagram.mmd --no-optimize
pidraw analyze input.dot --no-render
```

---

### pidraw optimize

Optimise an SVG file by running the optimisation pipeline.

**Usage:**

```bash
pidraw optimize <file> [--output <path>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--output` | `-o` | Output file path (default: stdout) |

**Examples:**

```bash
pidraw optimize output.svg
pidraw optimize output.svg -o output.min.svg -v
```

---

### pidraw batch

Render multiple diagram files to SVG in parallel.

**Usage:**

```bash
pidraw batch <paths...> [--output-dir <dir>] [--language <lang>] [--optimize] [--recursive] [--workers <n>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--output-dir` | | Output directory for SVGs |
| `--language` | `-l` | Language override for all files |
| `--optimize` | `-O` | Optimise each output SVG |
| `--recursive` | `-r` | Scan subdirectories recursively |
| `--workers` | `-w` | Number of parallel workers |

**Examples:**

```bash
pidraw batch input.mmd input.dot input.puml -O
pidraw batch *.mmd --output-dir ./out --recursive
pidraw batch diagrams/ --output-dir ./svgs -O -w 8 -v
```

---

### pidraw watch

Watch diagram files for changes and automatically re-render on save.

**Usage:**

```bash
pidraw watch <paths...> [--output-dir <dir>] [--language <lang>] [--optimize] [--recursive] [--debounce <sec>]
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--output-dir` | | Output directory for SVGs |
| `--language` | `-l` | Language override |
| `--optimize` | `-O` | Optimise rendered SVGs |
| `--recursive` | `-r` | Watch subdirectories recursively |
| `--debounce` | | Debounce interval in seconds (default: 1.0) |

**Examples:**

```bash
pidraw watch diagram.mmd
pidraw watch diagrams/ --output-dir ./svgs -O -r
pidraw watch *.mmd --debounce 0.5
```

---

### pidraw plugins

List all registered and discovered renderer plugins.

**Usage:**

```bash
pidraw plugins
```

**Examples:**

```bash
pidraw plugins
pidraw plugins -v
```

---

### pidraw version

Show the PiDraw version.

**Usage:**

```bash
pidraw version
```

---

### pidraw formats

List all supported diagram formats with their extensions and renderer information.

**Usage:**

```bash
pidraw formats
```

---

### pidraw benchmark

Run the PiDraw benchmark suite to measure rendering speed, optimization throughput, cache efficiency, and large-file performance.

**Usage:**

```bash
pidraw benchmark [--quick]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--quick` | Run fewer iterations for a faster result |

**Example output:**

```
============================================================
PiDraw Benchmark Report
============================================================
  System:      3.12.0, pid=12345
  Total time:  1542.3 ms

  [Render Speed]
    Render time:       12.34 ms
    Throughput:        45.6 diag/s

  [Optimization]
    Optimize time:     2.34 ms
    Output size:       1234 bytes

  [Cache Efficiency]
    Render time:       0.12 ms
    Cache hit rate:    100.0%

  [Large Diagram (500 nodes)]
    Render time:       234.56 ms
    Memory delta:      4.5 MB
    Output size:       45678 bytes
------------------------------------------------------------
```
