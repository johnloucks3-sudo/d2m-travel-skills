import os
import re

dossier_dir = '/home/john/Thunderbird/dossiers'
for filename in os.listdir(dossier_dir):
    if filename.endswith('.md'):
        filepath = os.path.join(dossier_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check if already has completed_tps
        if 'completed_tps:' not in content:
            # Find the end of frontmatter
            match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
            if match:
                new_frontmatter = match.group(1) + '\ncompleted_tps: []'
                new_content = content.replace(match.group(1), new_frontmatter)
                with open(filepath, 'w') as f:
                    f.write(new_content)
                print(f"Updated {filename}")
