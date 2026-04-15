import logging
from alembic.config import main
import sys

if __name__ == '__main__':
    try:
        sys.argv = ['alembic', 'upgrade', 'head']
        main()
    except Exception as e:
        import traceback; traceback.print_exc()
