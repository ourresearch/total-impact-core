from setuptools import setup, find_packages

setup(
    name = 'totalimpact',
    version = '0.2.0',
    packages = find_packages(),
    install_requires = [
        "Flask==0.7.2",
        "Flask-Login",
        "Flask-WTF",
        "couchdb",
        "requests",
        "BeautifulSoup"
				],
    url = '',
    author = 'Total Impact',
    author_email = '',
    description = 'Total Impact',
    license = '',
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)

