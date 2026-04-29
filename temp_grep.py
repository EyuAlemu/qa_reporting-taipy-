import os, pkgutil
import marshmallow
root = os.path.dirname(marshmallow.__file__)
for dirpath, dirs, files in os.walk(root):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(dirpath, file)
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            if 'Inferred' in text:
                print(path)
                break
