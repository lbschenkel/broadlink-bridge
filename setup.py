from setuptools import setup

setup(
    name='broadlink-bridge',
    version='0.1.8',
    packages=['broadlink_bridge'],
    entry_points={
        'console_scripts': [
            'broadlink-bridge=broadlink_bridge.cli:main'
        ],
    },
    install_requires=[
        'broadlink==0.18.0',
        'cryptography>=3.2',
        'paho-mqtt>=1.4.0',
    ],
)
