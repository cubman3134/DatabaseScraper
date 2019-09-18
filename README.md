# Database Scraper
Database Scraper is a generalized web scraper that places values from html files into a mysql database. Currently it is set up to scrape from historic runescape market data.
Scraper2.py scrapes 6 month prices for each item on the Grand Exchange Runescape Database and places them into my personal mysql database.
This program was also used to find these items and place them into files for webscraping later.
A few items might be missing from the files/database because Jagex doesn't like when you connect a ton from one IP.
Proxies were used to get past this, but being run with high amounts of multiprocessing can eliminate the effect.
There is more to be done with this project, I want to get it online for all to use at some point.

The general call to scrape the GrandExchange database to the mysql database is:

<b>python scraper2.py <mysql_password> < downloadall.txt</b>

Although other commands can be used as well as needed.
