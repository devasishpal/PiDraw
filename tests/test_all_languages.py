"""Test all language renderers and save SVG+PNG outputs."""
import os
from pathlib import Path
from pidraw.backend.png import svg_to_png

OUT = Path(r"C:\Users\Alok\Desktop\pidraw_test")
OUT.mkdir(parents=True, exist_ok=True)

def save(name, svg):
    svg_path = OUT / f"{name}.svg"
    png_path = OUT / f"{name}.png"
    svg_path.write_text(svg, encoding="utf-8")
    try:
        png = svg_to_png(svg, transparent=True, trim=True)
        png_path.write_bytes(png)
        png_ok = True
    except Exception as e:
        png = svg_to_png(svg, transparent=False, trim=False)
        png_path.write_bytes(png)
        png_ok = f"fallback ({e})"
    print(f"  {name}: SVG {len(svg)} bytes, PNG {png_path.stat().st_size if png_path.exists() else 0} bytes (PNG: {png_ok})")

from pidraw import render

# 1. Mermaid flowchart
print("\n1. Mermaid (flowchart)")
save("mermaid_flowchart", render("graph TD; A[Start] --> B{Is it working?}; B -->|Yes| C[Great!]; B -->|No| D[Fix it]; D --> B", language="mermaid").svg)

# 2. Mermaid sequenceDiagram
print("\n2. Mermaid (sequenceDiagram)")
save("mermaid_sequence", render("sequenceDiagram; participant Alice; participant Bob; Alice->>John: Hello; John-->>Alice: Hi!", language="mermaid").svg)

# 3. Mermaid classDiagram
print("\n3. Mermaid (classDiagram)")
save("mermaid_class", render("classDiagram; class Animal { +name; +age }; class Dog { +breed }; Animal <|-- Dog", language="mermaid").svg)

# 4. Mermaid stateDiagram
print("\n4. Mermaid (stateDiagram)")
save("mermaid_state", render("stateDiagram-v2; [*] --> Still; Still --> Moving; Moving --> [*]", language="mermaid").svg)

# 5. Mermaid erDiagram
print("\n5. Mermaid (erDiagram)")
save("mermaid_er", render("erDiagram; CUSTOMER ||--o{ ORDER : places", language="mermaid").svg)

# 6. Mermaid pie
print("\n6. Mermaid (pie)")
save("mermaid_pie", render('pie; "Dogs" : 386; "Cats" : 85; "Rats" : 15', language="mermaid").svg)

# 7. Mermaid gantt
print("\n7. Mermaid (gantt)")
save("mermaid_gantt", render("gantt; dateFormat YYYY-MM-DD; section S; A task: 2014-01-01, 30d", language="mermaid").svg)

# 8. PlantUML
print("\n8. PlantUML")
save("plantuml", render("@startuml\nA --> B\n@enduml", language="plantuml").svg)

# 9. Graphviz
print("\n9. Graphviz")
save("graphviz", render("digraph G { A -> B; B -> C; A -> C }", language="graphviz").svg)

# 10. D2
print("\n10. D2")
save("d2", render("A -> B: hello", language="d2").svg)

# 11. ASCII
print("\n11. ASCII")
save("ascii", render("+---+ --> +---+", language="ascii").svg)

# 12. Markmap
print("\n12. Markmap")
save("markmap", render("# Root\n## Section 1\n### Detail", language="markmap").svg)

# 13. Nomnoml
print("\n13. Nomnoml")
save("nomnoml", render("[Customer]-[Order]", language="nomnoml").svg)

# 14. WaveDrom
print("\n14. WaveDrom")
save("wavedrom", render('{"signal":[{"name":"clk","wave":"P"}]}', language="wavedrom").svg)

# 15. Structurizr
print("\n15. Structurizr")
save("structurizr", render('workspace {\n  model {\n    user = person "User"\n    system = softwareSystem "My System"\n    user -> system "Uses"\n  }\n}', language="structurizr").svg)

# 16. BPMN
print("\n16. BPMN")
bpmn_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="def_1" targetNamespace="http://example.com">
  <process id="Process_1" isExecutable="false">
    <startEvent id="Start_1" name="Start"/>
    <task id="Task_1" name="Process"/>
    <endEvent id="End_1" name="End"/>
    <sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1"/>
    <sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1"/>
  </process>
</definitions>'''
save("bpmn", render(bpmn_xml, language="bpmn").svg)

# 17. Vega-Lite
print("\n17. Vega-Lite")
save("vega_lite", render('{"$schema":"https://vega.github.io/schema/vega-lite/v5.json","mark":"bar","data":{"values":[{"a":"A","b":28},{"a":"B","b":55}]},"encoding":{"x":{"field":"a"},"y":{"field":"b","type":"quantitative"}}}', language="vega-lite").svg)

# 18. Excalidraw
print("\n18. Excalidraw")
save("excalidraw", render('{"type":"excalidraw","elements":[{"id":"a","type":"rectangle","x":0,"y":0,"width":100,"height":60,"strokeColor":"#000","backgroundColor":"#fff","text":"Hello"},{"id":"b","type":"arrow","points":[[0,0],[120,0]],"startBinding":{"elementId":"a"},"endBinding":{"elementId":"c"}},{"id":"c","type":"ellipse","x":200,"y":0,"width":80,"height":60,"strokeColor":"#000","backgroundColor":"#fff","text":"World"}]}', language="excalidraw").svg)

# 19. TikZ
print("\n19. TikZ")
save("tikz", render("\\node[draw] (a) {Hello}; \\node[draw,circle] (b) at (3,0) {World}; \\draw[->] (a) -- (b);", language="tikz").svg)

# 20. Vega (full)
print("\n20. Vega")
save("vega", render('{"$schema":"https://vega.github.io/schema/vega/v5.json","width":200,"height":200,"marks":[{"type":"symbol","encode":{"enter":{"x":{"value":100},"y":{"value":100},"size":{"value":100},"shape":{"value":"circle"}}}}]}', language="vega").svg)

print("\n=== ALL DONE ===")
print(f"Output directory: {OUT}")
