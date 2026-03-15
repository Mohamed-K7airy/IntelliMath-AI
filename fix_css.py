
import os

file_path = r'c:\Users\Administrator\Desktop\WE\style.css'

with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Terminate at line 2010 (the end of the lanyard styles)
clean_lines = []
for i, line in enumerate(lines):
    if i >= 2010: 
        break
    clean_lines.append(line)

dept_styles = """
/* Department Section Styles */
.department-section {
    margin-bottom: 80px;
}

.section-subtitle {
    font-family: 'Etna Sans Serif', 'Arial Black', Impact, sans-serif;
    font-size: clamp(24px, 4vw, 40px);
    font-weight: 800;
    text-align: center;
    color: #FFFFFF;
    margin-bottom: 10px;
    letter-spacing: 2px;
}

.pharaonic-line.mini {
    margin-bottom: 40px;
    transform: scale(0.7);
}

.pharaonic-line.mini .line {
    height: 1px;
    background: linear-gradient(to right, transparent, var(--bg-orange), transparent);
}
"""

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)
    f.write(dept_styles)

print("Successfully cleaned and updated style.css with department designs.")
