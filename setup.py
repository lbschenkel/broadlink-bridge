from setuptools import setup

setup(
    name='broadlink-bridge',
    version='0.1.4',
    packages=['broadlink_bridge'],
    entry_points={
        'console_scripts': [
            'broadlink-bridge=broadlink_bridge.cli:main'
        ],
    },
    install_requires=[
        'broadlink==0.14.0',
        'cryptography>=2.6',
        'paho-mqtt>=1.4.0',
    ],
)