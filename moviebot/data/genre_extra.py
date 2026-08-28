"""
Extra hand-picked titles per genre, used to round out the "Top by Genre"
lists (Romance / Drama / Comedy / Action / Sci-Fi / Horror) beyond what's
already present in imdb_top.py. Same tuple format:
(title, year, type, imdb, rt, meta, genres)
"""

GENRE_EXTRA = {
    "Romance": [
        ("Titanic", 1997, "movie", 7.9, 88, 75, ["Romance", "Drama"]),
        ("Pride & Prejudice", 2005, "movie", 7.8, 87, 82, ["Romance", "Drama"]),
        ("La La Land", 2016, "movie", 8.0, 91, 94, ["Romance", "Musical", "Drama"]),
        ("The Notebook", 2004, "movie", 7.8, 53, 53, ["Romance", "Drama"]),
        ("Before Sunrise", 1995, "movie", 8.1, 100, 77, ["Romance", "Drama"]),
        ("Before Sunset", 2004, "movie", 8.1, 95, 90, ["Romance", "Drama"]),
        ("500 Days of Summer", 2009, "movie", 7.7, 85, 76, ["Romance", "Comedy", "Drama"]),
        ("Call Me by Your Name", 2017, "movie", 7.9, 95, 93, ["Romance", "Drama"]),
        ("Pride and Prejudice and Zombies", 2016, "movie", 5.9, 40, 47, ["Romance", "Comedy", "Horror"]),
        ("The Fault in Our Stars", 2014, "movie", 7.7, 80, 69, ["Romance", "Drama"]),
        ("Notting Hill", 1999, "movie", 7.2, 84, 58, ["Romance", "Comedy"]),
        ("A Walk to Remember", 2002, "movie", 7.3, 30, 42, ["Romance", "Drama"]),
        ("Crazy Rich Asians", 2018, "movie", 6.9, 91, 74, ["Romance", "Comedy"]),
        ("Her", 2013, "movie", 8.0, 94, 91, ["Romance", "Drama", "Sci-Fi"]),
        ("The Princess Bride", 1987, "movie", 8.0, 97, 77, ["Adventure", "Family", "Fantasy"]),
    ],
    "Comedy": [
        ("The Grand Budapest Hotel", 2014, "movie", 8.1, 92, 88, ["Comedy", "Drama"]),
        ("Superbad", 2007, "movie", 7.6, 88, 76, ["Comedy"]),
        ("Bridesmaids", 2011, "movie", 6.8, 90, 75, ["Comedy", "Romance"]),
        ("The Hangover", 2009, "movie", 7.7, 79, 73, ["Comedy"]),
        ("Groundhog Day", 1993, "movie", 8.0, 96, 72, ["Comedy", "Fantasy", "Romance"]),
        ("Monty Python and the Holy Grail", 1975, "movie", 8.2, 97, 91, ["Comedy", "Adventure", "Fantasy"]),
        ("Knives Out", 2019, "movie", 7.9, 97, 82, ["Comedy", "Crime", "Drama"]),
        ("Airplane!", 1980, "movie", 7.7, 96, 78, ["Comedy"]),
        ("Ferris Bueller's Day Off", 1986, "movie", 7.8, 80, 62, ["Comedy"]),
        ("Jojo Rabbit", 2019, "movie", 7.9, 80, 58, ["Comedy", "Drama", "War"]),
        ("The Big Lebowski", 1998, "movie", 8.1, 79, 71, ["Comedy", "Crime"]),
        ("Shaun of the Dead", 2004, "movie", 7.9, 92, 76, ["Comedy", "Horror"]),
    ],
    "Action": [
        ("Mad Max: Fury Road", 2015, "movie", 8.1, 97, 90, ["Action", "Adventure", "Sci-Fi"]),
        ("John Wick", 2014, "movie", 7.4, 86, 68, ["Action", "Crime", "Thriller"]),
        ("Die Hard", 1988, "movie", 8.2, 94, 88, ["Action", "Thriller"]),
        ("Mission: Impossible - Fallout", 2018, "movie", 7.7, 97, 86, ["Action", "Adventure", "Thriller"]),
        ("The Raid: Redemption", 2011, "movie", 7.6, 86, 74, ["Action", "Crime", "Thriller"]),
        ("Top Gun: Maverick", 2022, "movie", 8.2, 96, 78, ["Action", "Drama"]),
        ("Dunkirk", 2017, "movie", 7.8, 92, 94, ["Action", "Drama", "History"]),
        ("Kill Bill: Vol. 1", 2003, "movie", 8.2, 85, 69, ["Action", "Crime", "Thriller"]),
        ("Skyfall", 2012, "movie", 7.8, 93, 81, ["Action", "Adventure", "Thriller"]),
        ("The Raid 2", 2014, "movie", 7.9, 79, 76, ["Action", "Crime", "Thriller"]),
    ],
    "Drama": [
        ("A Beautiful Mind", 2001, "movie", 8.2, 74, 72, ["Biography", "Drama"]),
        ("Manchester by the Sea", 2016, "movie", 7.8, 96, 96, ["Drama"]),
        ("Moonlight", 2016, "movie", 7.4, 98, 99, ["Drama"]),
        ("There Will Be Blood", 2007, "movie", 8.2, 91, 92, ["Drama"]),
        ("The Social Network", 2010, "movie", 7.7, 96, 95, ["Biography", "Drama"]),
        ("Nomadland", 2020, "movie", 7.3, 93, 93, ["Drama"]),
        ("12 Years a Slave", 2013, "movie", 8.1, 95, 96, ["Biography", "Drama", "History"]),
        ("Marriage Story", 2019, "movie", 7.9, 94, 94, ["Comedy", "Drama", "Romance"]),
        ("Room", 2015, "movie", 8.1, 93, 86, ["Drama"]),
    ],
    "Sci-Fi": [
        ("Blade Runner 2049", 2017, "movie", 8.0, 88, 81, ["Sci-Fi", "Drama"]),
        ("Arrival", 2016, "movie", 7.9, 94, 81, ["Sci-Fi", "Drama"]),
        ("Dune", 2021, "movie", 8.0, 83, 74, ["Sci-Fi", "Adventure", "Drama"]),
        ("Edge of Tomorrow", 2014, "movie", 7.9, 90, 71, ["Sci-Fi", "Action"]),
        ("Ex Machina", 2014, "movie", 7.7, 92, 78, ["Sci-Fi", "Drama", "Thriller"]),
        ("District 9", 2009, "movie", 7.9, 90, 81, ["Sci-Fi", "Action", "Thriller"]),
    ],
    "Horror": [
        ("Hereditary", 2018, "movie", 7.3, 90, 87, ["Horror", "Drama", "Mystery"]),
        ("Get Out", 2017, "movie", 7.7, 98, 85, ["Horror", "Mystery", "Thriller"]),
        ("The Exorcist", 1973, "movie", 8.1, 78, 81, ["Horror"]),
        ("A Quiet Place", 2018, "movie", 7.5, 96, 82, ["Horror", "Drama", "Sci-Fi"]),
        ("The Conjuring", 2013, "movie", 7.5, 86, 68, ["Horror", "Mystery", "Thriller"]),
        ("Midsommar", 2019, "movie", 7.1, 83, 72, ["Horror", "Drama", "Mystery"]),
    ],
}
