import sys
import os

# Добавляем корневую директорию проекта (на один уровень выше, чем 'tests')
# в PYTHONPATH. Это позволит тестам импортировать модули из пакета 'bot'.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    