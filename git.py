import os
import subprocess


def get_git_revision_short_hash():
    try:
        with open(os.devnull, 'w') as devnull:
            return str(subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                stderr=devnull), 'ascii').strip()
    except subprocess.CalledProcessError:
        pass
