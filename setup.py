import os

from setuptools import setup
from setuptools import find_packages

# TODO This isn't working
#os.system("pandoc --from=markdown --to=rst --output=README.rst README.md")


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join)
    in a platform-neutral way.
    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

EXCLUDE_FROM_PACKAGES  = []

def is_package(package_name):
    for pkg in EXCLUDE_FROM_PACKAGES:
        if package_name.startswith(pkg):
            return False
    return True


# Compile the list of packages available, because distutils doesn't have
# an easy way to do this.
packages, package_data = [], {}

root_dir = os.path.dirname(__file__)
if root_dir != '':
    os.chdir(root_dir)
#anouman_dir = 'anouman'

for dirpath, dirnames, filenames in os.walk("vagabond"):
    # Ignore PEP 3147 cache dirs and those whose names start with '.'
    dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
    parts = fullsplit(dirpath)
    package_name = '.'.join(parts)
    if '__init__.py' in filenames and is_package(package_name):
        packages.append(package_name)
    elif filenames:
        relative_path = []
        while '.'.join(parts) not in packages:
            relative_path.append(parts.pop())
        relative_path.reverse()
        path = os.path.join(*relative_path)
        package_files = package_data.setdefault('.'.join(parts), [])
        package_files.extend([os.path.join(path, f) for f in filenames])

    
with open('README.rst') as file:
    long_description = file.read()

setup(
    name='vagabond',
    version='0.0.1',
    description='python tool to create portable development environments',
    long_description=(read('README.rst') + '\n\n' +
                      read('HISTORY.rst') + '\n\n' +
                      read('AUTHORS.rst')),
    url='https://github.com/gnulnx/vagabond.git',
    license='MIT',
    author='John Furr',
    author_email='john.furr@gmail.com',
    py_modules=['bin', 'vagabond', 'vagabond/templates'],
    scripts=['bin/vagabond'],
    include_package_data=True,
    #packages=['bin', 'vagabond'],
    packages=find_packages(),
    package_data=package_data,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=[
        "django", 
        "requests",
        "clint",
        "logutils",
        "Jinja2==2.11.3"
    ],
    test_suite="tests"
)
