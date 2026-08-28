"""
Sample built-in filmography data for a set of very well-known actors and
directors, so actor/director search works offline out of the box.

This obviously can't cover every person in existence — for unlimited,
live search of ANY actor or director, set TMDB_API_KEY in .env (free,
see README) and the bot will query TMDb's full database instead.

Keys are lowercased for matching.
"""

ACTORS = {
    "leonardo dicaprio": [
        "Inception (2010) - IMDb 8.8", "The Revenant (2015) - IMDb 8.0",
        "The Wolf of Wall Street (2013) - IMDb 8.2", "Titanic (1997) - IMDb 7.9",
        "Django Unchained (2012) - IMDb 8.5", "Shutter Island (2010) - IMDb 8.2",
        "The Departed (2006) - IMDb 8.5", "Catch Me If You Can (2002) - IMDb 8.1",
        "Once Upon a Time in Hollywood (2019) - IMDb 7.6", "The Great Gatsby (2013) - IMDb 7.2",
    ],
    "tom hanks": [
        "Forrest Gump (1994) - IMDb 8.8", "Saving Private Ryan (1998) - IMDb 8.6",
        "Cast Away (2000) - IMDb 7.8", "The Green Mile (1999) - IMDb 8.6",
        "Toy Story (1995) - IMDb 8.3", "Catch Me If You Can (2002) - IMDb 8.1",
        "Apollo 13 (1995) - IMDb 7.6", "Big (1988) - IMDb 7.4",
        "Philadelphia (1993) - IMDb 7.7", "Captain Phillips (2013) - IMDb 7.8",
    ],
    "meryl streep": [
        "The Devil Wears Prada (2006) - IMDb 6.9", "Sophie's Choice (1982) - IMDb 8.0",
        "Kramer vs. Kramer (1979) - IMDb 7.8", "The Iron Lady (2011) - IMDb 6.4",
        "Mamma Mia! (2008) - IMDb 6.4", "Doubt (2008) - IMDb 7.5",
        "Julie & Julia (2009) - IMDb 7.0", "The Post (2017) - IMDb 7.2",
        "Out of Africa (1985) - IMDb 7.2", "Little Women (2019) - IMDb 7.8",
    ],
    "robert downey jr": [
        "Iron Man (2008) - IMDb 7.9", "Avengers: Endgame (2019) - IMDb 8.4",
        "Sherlock Holmes (2009) - IMDb 7.6", "Oppenheimer (2023) - IMDb 8.3",
        "Chaplin (1992) - IMDb 7.7", "Tropic Thunder (2008) - IMDb 7.0",
        "Zodiac (2007) - IMDb 7.7", "The Avengers (2012) - IMDb 8.0",
        "Iron Man 3 (2013) - IMDb 7.1", "Captain America: Civil War (2016) - IMDb 7.8",
    ],
    "scarlett johansson": [
        "Lost in Translation (2003) - IMDb 7.7", "Her (2013) - IMDb 8.0",
        "Avengers: Endgame (2019) - IMDb 8.4", "Marriage Story (2019) - IMDb 7.9",
        "Jojo Rabbit (2019) - IMDb 7.9", "Lucy (2014) - IMDb 6.4",
        "The Avengers (2012) - IMDb 8.0", "Under the Skin (2013) - IMDb 6.3",
        "Black Widow (2021) - IMDb 6.7", "Match Point (2005) - IMDb 7.4",
    ],
    "brad pitt": [
        "Fight Club (1999) - IMDb 8.8", "Se7en (1995) - IMDb 8.6",
        "Once Upon a Time in Hollywood (2019) - IMDb 7.6", "Inglourious Basterds (2009) - IMDb 8.3",
        "Twelve Monkeys (1995) - IMDb 8.0", "Moneyball (2011) - IMDb 7.6",
        "The Curious Case of Benjamin Button (2008) - IMDb 7.8", "Ocean's Eleven (2001) - IMDb 7.7",
        "World War Z (2013) - IMDb 7.0", "Troy (2004) - IMDb 7.2",
    ],
}

DIRECTORS = {
    "christopher nolan": [
        "The Dark Knight (2008) - IMDb 9.0", "Inception (2010) - IMDb 8.8",
        "Interstellar (2014) - IMDb 8.7", "The Prestige (2006) - IMDb 8.5",
        "Memento (2000) - IMDb 8.4", "Oppenheimer (2023) - IMDb 8.3",
        "Dunkirk (2017) - IMDb 7.8", "Batman Begins (2005) - IMDb 8.2",
        "The Dark Knight Rises (2012) - IMDb 8.4", "Tenet (2020) - IMDb 7.3",
    ],
    "martin scorsese": [
        "Goodfellas (1990) - IMDb 8.7", "Taxi Driver (1976) - IMDb 8.2",
        "The Departed (2006) - IMDb 8.5", "The Wolf of Wall Street (2013) - IMDb 8.2",
        "Raging Bull (1980) - IMDb 8.2", "Casino (1995) - IMDb 8.2",
        "Shutter Island (2010) - IMDb 8.2", "The Irishman (2019) - IMDb 7.8",
        "Gangs of New York (2002) - IMDb 7.5", "Killers of the Flower Moon (2023) - IMDb 7.6",
    ],
    "steven spielberg": [
        "Schindler's List (1993) - IMDb 9.0", "Saving Private Ryan (1998) - IMDb 8.6",
        "Jurassic Park (1993) - IMDb 8.2", "E.T. the Extra-Terrestrial (1982) - IMDb 7.9",
        "Jaws (1975) - IMDb 8.1", "Raiders of the Lost Ark (1981) - IMDb 8.4",
        "Catch Me If You Can (2002) - IMDb 8.1", "Munich (2005) - IMDb 7.5",
        "Lincoln (2012) - IMDb 7.3", "West Side Story (2021) - IMDb 7.1",
    ],
    "quentin tarantino": [
        "Pulp Fiction (1994) - IMDb 8.9", "Kill Bill: Vol. 1 (2003) - IMDb 8.2",
        "Inglourious Basterds (2009) - IMDb 8.3", "Django Unchained (2012) - IMDb 8.5",
        "Reservoir Dogs (1992) - IMDb 8.3", "Once Upon a Time in Hollywood (2019) - IMDb 7.6",
        "Jackie Brown (1997) - IMDb 7.5", "Kill Bill: Vol. 2 (2004) - IMDb 8.0",
        "Death Proof (2007) - IMDb 6.9", "The Hateful Eight (2015) - IMDb 7.8",
    ],
    "denis villeneuve": [
        "Blade Runner 2049 (2017) - IMDb 8.0", "Dune (2021) - IMDb 8.0",
        "Arrival (2016) - IMDb 7.9", "Sicario (2015) - IMDb 7.6",
        "Prisoners (2013) - IMDb 8.1", "Dune: Part Two (2024) - IMDb 8.5",
        "Incendies (2010) - IMDb 8.2", "Enemy (2013) - IMDb 6.9",
    ],
    "bong joon ho": [
        "Parasite (2019) - IMDb 8.5", "Memories of Murder (2003) - IMDb 8.1",
        "Snowpiercer (2013) - IMDb 7.0", "The Host (2006) - IMDb 7.0",
        "Mother (2009) - IMDb 7.9", "Okja (2017) - IMDb 7.0",
    ],
}
