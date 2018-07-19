# Instaseek : find your influencers on Instagram

## Setup

- Install Python 3.6: https://www.python.org/downloads/release/python-360/
- `pip install -r requirements.txt` to install Python dependencies

## Manual

This project aims to detect genuine and organic influencers on Instagram. The model is data-based and uses a machine learning approach :

- Simple metrics such as followers, following, media count, mean engagement rate, post frequency, etc.
- Comment quality score: is the audience engaged ?
- Metrics over the feed images' quality : unity of contrast and colofulness, redundancy of colors, etc.

## Script files

- `annotation_tool.py` helped me to annotate influencers streamed in the database.
- `classifier.py` lets you analyze an Instagram profile and classifies it among inlfuencer/not influencer.
- `main.py` is the entrypoint. Currently, it lauches `streamer.py`.
- `sql_client.py` is the SQL client. It processes and creates SQL requests to the database.
- `streamer.py` streams Instagram content into the database.
- `train.py` trains the model with data available in the database.
- `user.py` processes user infomation and extracts feature for machine learning.
- `utils.py` gathers all utility functions.

## Contact

Valentin Berthelot

valentin.berthelot@imt-atlantique.fr
valentin.berthelot5@gmail.com

