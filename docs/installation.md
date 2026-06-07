# Installation

## Requirements

- Python 3.10 or later

## Install from PyPI

Stable release:

```
pip install pidraw
```

Install with extra dependency groups:

```
pip install pidraw[dev]       # development tools (testing, linting)
pip install pidraw[docs]       # documentation build tools
pip install pidraw[all]        # all extras
```

## Install from Source

Clone the repository and install in editable mode:

```
git clone https://github.com/yourusername/pidraw.git
cd pidraw
pip install -e .
```

To include all extras from source:

```
pip install -e ".[all]"
```

## Verify Installation

Check the CLI works:

```
pidraw --version
```

Check the Python package imports correctly:

```
python -c "import pidraw; print(pidraw.__version__)"
```

## Optional Renderer Dependencies

PiDraw delegates rendering to external CLI tools. Install the ones you need:

| Renderer   | Binary      | Install                                                    |
|------------|-------------|------------------------------------------------------------|
| Mermaid    | `mmdc`      | `npm install -g @mermaid-js/mermaid-cli`                   |
| Graphviz   | `dot`       | `winget install graphviz` or download from graphviz.org    |
| PlantUML   | `java -jar plantuml.jar` | Download `plantuml.jar` from plantuml.com           |
| D2         | `d2`        | `winget install d2` or download from d2lang.com            |

PiDraw will automatically discover these tools on your PATH at runtime. If a renderer is unavailable, PiDraw reports a clear error message indicating which binary is missing.

## Troubleshooting

### "pidraw: command not found"

Ensure your Python Scripts directory is on your PATH:

```
python -m site --user-base
```

Add the `Scripts` subdirectory of the output path to your system PATH.

### Renderer not found

Run the verification command for the specific renderer:

```
mmdc --version   # Mermaid
dot -V           # Graphviz
java -jar plantuml.jar -version  # PlantUML
d2 version       # D2
```

If a binary is not found, install it following the table above and ensure its location is on your PATH.

### ImportError or version mismatch

Upgrade to the latest release:

```
pip install --upgrade pidraw
```

If the issue persists, check the [GitHub Issues](https://github.com/yourusername/pidraw/issues) page.
