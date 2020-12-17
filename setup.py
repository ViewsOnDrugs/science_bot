#!/usr/bin/env python3
from setuptools import setup

setup(
    name="scibot",
    version="0.1",
    description="Bot for sci-com and policy-com ",
    url="https://github.com/fanasal/science_bot",
    license="GNU Affero General Public License v3.0",
    packages=["scibot"],
    keywords=[
        "psychedelics",
        "fact-checking",
        "sci-com",
        "drug policy",
        "research",
	"science",
    ],
    entry_points={
        "console_scripts": [
            "scibot=scibot.what_a_c:main",
        ]
    },
    install_requires=["tweepy",
                    "feedparser",
                    "schedule",
                    "python-dotenv",],
    zip_safe=False,

)
