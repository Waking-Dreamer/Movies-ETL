# Module 8 Challenge

# Import dependencies
import json
import pandas as pd
import numpy as np
import re
from sqlalchemy import create_engine
from config import db_password
import time

# Create function to take in 3 arguments (data files), clean data, and load into SQL
def extract_transform_load(wiki_movies_df, kaggle_metadata, ratings):
    
    # Define file directory variable
    file_dir = "/Users/SamWise/Data_Analytics/Modules/8_ETL/Movies-ETL"

    # Define data file arguments 
    kaggle_metadata = pd.read_csv(f'{file_dir}/movies_metadata.csv', low_memory=False)
    ratings = pd.read_csv(f'{file_dir}/ratings.csv')

    #Convert wiki file then define
    with open(f'{file_dir}/wikipedia.movies.json', mode='r') as file:
        wiki_movies_raw = json.load(file)
    wiki_movies_df = pd.DataFrame(wiki_movies_raw)

    # Filter and clean Wiki data
    try:
        # Filter movies into new list
        wiki_movies = [movie for movie in wiki_movies_raw
                if ('Director' in movie or 'Directed by' in movie)
                    and 'imdb_link' in movie
                    and 'No. of episodes' not in movie]
        wiki_movies_df = pd.DataFrame(wiki_movies)

        # Create fucntion to make copy of the movie and return it
        def clean_movie(movie):
            movie = dict(movie)
        
        # Combine all alternate titles columns into one
            alt_titles = {}
            for key in ['Also known as','Arabic','Cantonese','Chinese','French',
                    'Hangul','Hebrew','Hepburn','Japanese','Literally',
                    'Mandarin','McCune–Reischauer','Original title','Polish',
                    'Revised Romanization','Romanized','Russian',
                    'Simplified','Traditional','Yiddish']:
                if key in movie:
                    alt_titles[key] = movie[key]
                    movie.pop(key)
            if len(alt_titles) > 0:
                movie['alt_titles'] = alt_titles

            # merge column names
            def change_column_name(old_name, new_name):
                if old_name in movie:
                    movie[new_name] = movie.pop(old_name)
            change_column_name('Adaptation by', 'Writer(s)')
            change_column_name('Country of origin', 'Country')
            change_column_name('Directed by', 'Director')
            change_column_name('Distributed by', 'Distributor')
            change_column_name('Edited by', 'Editor(s)')
            change_column_name('Length', 'Running time')
            change_column_name('Original release', 'Release date')
            change_column_name('Music by', 'Composer(s)')
            change_column_name('Produced by', 'Producer(s)')
            change_column_name('Producer', 'Producer(s)')
            change_column_name('Productioncompanies ', 'Production company(s)')
            change_column_name('Productioncompany ', 'Production company(s)')
            change_column_name('Released', 'Release Date')
            change_column_name('Release Date', 'Release date')
            change_column_name('Screen story by', 'Writer(s)')
            change_column_name('Screenplay by', 'Writer(s)')
            change_column_name('Story by', 'Writer(s)')
            change_column_name('Theme music composer', 'Composer(s)')
            change_column_name('Written by', 'Writer(s)')     
            
            return movie

        # make a list of cleaned movies with a list comprehension
        clean_movies = [clean_movie(movie) for movie in wiki_movies]    

        # Set wiki_movies_df to be the DataFrame created from clean_movies
        wiki_movies_df = pd.DataFrame(clean_movies)

        # Extract string text
        wiki_movies_df['imdb_id'] = wiki_movies_df['imdb_link'].str.extract(r'(tt\d{7})')

        # Drop duplicate IMDb IDs
        wiki_movies_df.drop_duplicates(subset='imdb_id', inplace=True)

        # Drop missing values from the box office field and store in df
        box_office = wiki_movies_df['Box office'].dropna()

        # View box office values
        box_office = box_office.apply(lambda x: ' '.join(x) if type(x) == list else x)

        # Use regular expression to search for box office values (words)
        form_one = r'\$\s*\d+\.?\d*\s*[mb]illi?on'
        box_office.str.contains(form_one, flags=re.IGNORECASE).sum()

        # Use regular expression to search for box office values (numbers)
        form_two = r'\$\s*\d{1,3}(?:[,\.]\d{3})+(?!\s[mb]illion)'
        box_office.str.contains(form_two, flags=re.IGNORECASE).sum()

        #Search for values that are given as a range
        box_office = box_office.str.replace(r'\$.*[-—–](?![a-z])', '$', regex=True)
    
        # Create fucntion to convert the Box Office Values
        def parse_dollars(s):
            # if s is not a string, return NaN
            if type(s) != str:
                return np.nan

            # if input is of the form $###.# million
            if re.match(r'\$\s*\d+\.?\d*\s*milli?on', s, flags=re.IGNORECASE):

                # remove dollar sign and " million"
                s = re.sub('\$|\s|[a-zA-Z]','', s)

                # convert to float and multiply by a million
                value = float(s) * 10**6

                # return value
                return value

            # if input is of the form $###.# billion
            elif re.match(r'\$\s*\d+\.?\d*\s*billi?on', s, flags=re.IGNORECASE):

                # remove dollar sign and " billion"
                s = re.sub('\$|\s|[a-zA-Z]','', s)

                # convert to float and multiply by a billion
                value = float(s) * 10**9

                # return value
                return value

            # if input is of the form $###,###,###
            elif re.match(r'\$\s*\d{1,3}(?:[,\.]\d{3})+(?!\s[mb]illion)', s, flags=re.IGNORECASE):

                # remove dollar sign and commas
                s = re.sub('\$|,','', s)

                # convert to float
                value = float(s)

                # return value
                return value

            # otherwise, return NaN
            else:
                return np.nan

        # Parse the box office values to numeric values
        wiki_movies_df['box_office'] = box_office.str.extract(f'({form_one}|{form_two})', flags=re.IGNORECASE)[0].apply(parse_dollars)
    
        # Drop box office column
        wiki_movies_df.drop('Box office', axis=1, inplace=True)

        # Create budget variable
        budget = wiki_movies_df['Budget'].dropna()

        # Convert any lists to strings
        budget = budget.map(lambda x: ' '.join(x) if type(x) == list else x)

        # Remove any values between a dollar sign and hyphen
        budget = budget.str.replace(r'\$.*[-—–](?![a-z])', '$', regex=True)

        # Remove Citation references
        budget = budget.str.replace(r'\[\d+\]\s*', '')

        # Parse the budget values
        wiki_movies_df['budget'] = budget.str.extract(f'({form_one}|{form_two})', flags=re.IGNORECASE)[0].apply(parse_dollars)

        # Drop original budget column
        wiki_movies_df.drop('Budget', axis=1, inplace=True)

        # make a variable that holds the non-null values of Release date in the DataFrame, converting lists to strings
        release_date = wiki_movies_df['Release date'].dropna().apply(lambda x: ' '.join(x) if type(x) == list else x)

        # Use regular expressions to parse the Release Date data forms
        date_form_one = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s[123]\d,\s\d{4}'
        date_form_two = r'\d{4}.[01]\d.[123]\d'
        date_form_three = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}'
        date_form_four = r'\d{4}'

        # Extract the Dates
        release_date.str.extract(f'({date_form_one}|{date_form_two}|{date_form_three}|{date_form_four})', flags=re.IGNORECASE)
            
        # Parse release date data
        wiki_movies_df['release_date'] = pd.to_datetime(release_date.str.extract(f'({date_form_one}|{date_form_two}|{date_form_three}|{date_form_four})')[0], infer_datetime_format=True)

        # make a variable that holds the non-null values of Release date in the DataFrame, converting lists to strings
        running_time = wiki_movies_df['Running time'].dropna().apply(lambda x: ' '.join(x) if type(x) == list else x)

        # Extract Digits with RegEx
        running_time_extract = running_time.str.extract(r'(\d+)\s*ho?u?r?s?\s*(\d*)|(\d+)\s*m')

        # Convert all strings to numeric values
        running_time_extract = running_time_extract.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(0)

        # convert the hour capture groups and minute capture groups to minutes 
        wiki_movies_df['running_time'] = running_time_extract.apply(lambda row: row[0]*60 + row[1] if row[2] == 0 else row[2], axis=1)

        # Drop the Run time coulmn from the data set
        wiki_movies_df.drop('Running time', axis=1, inplace=True)

    except:
        print("An error occured cleaning the wiki data file, review for details")

    try:
        # Keep rows where the adult column is False, and then drop the adult column
        kaggle_metadata = kaggle_metadata[kaggle_metadata['adult'] == 'False'].drop('adult',axis='columns')

        # Convet non-boolean values
        kaggle_metadata['video'] = kaggle_metadata['video'] == 'True'

        # Convert numeric columns and raise an error if any data can't be converted
        kaggle_metadata['budget'] = kaggle_metadata['budget'].astype(int)
        kaggle_metadata['id'] = pd.to_numeric(kaggle_metadata['id'], errors='raise')
        kaggle_metadata['popularity'] = pd.to_numeric(kaggle_metadata['popularity'], errors='raise')

        # Convert release_date to datetime
        kaggle_metadata['release_date'] = pd.to_datetime(kaggle_metadata['release_date'])

        # Assign to timestamp column
        ratings['timestamp'] = pd.to_datetime(ratings['timestamp'], unit='s')
    
    except:
        print("An error occured cleaning the kaggle data file data, review for details")

    try:
        # merge data sets
        movies_df = pd.merge(wiki_movies_df, kaggle_metadata, on='imdb_id', suffixes=['_wiki','_kaggle'])

        # Drop the title_wiki, release_date_wiki, Language, and Production company(s) columns
        movies_df.drop(columns=['title_wiki','release_date_wiki','Language','Production company(s)'], inplace=True)

        # Create function to fill in missing data for a column pair then drop the redundant column
        def fill_missing_kaggle_data(df, kaggle_column, wiki_column):
            df[kaggle_column] = df.apply(
                lambda row: row[wiki_column] if row[kaggle_column] == 0 else row[kaggle_column]
                , axis=1)
            df.drop(columns=wiki_column, inplace=True)

        # Run function on columns
        fill_missing_kaggle_data(movies_df, 'runtime', 'running_time')
        fill_missing_kaggle_data(movies_df, 'budget_kaggle', 'budget_wiki')
        fill_missing_kaggle_data(movies_df, 'revenue', 'box_office')

        # Drop the video column
        movies_df.drop(columns=['video'], inplace=True)

        # Reorder columns to make then easier to read.
        movies_df = movies_df.loc[:, ['imdb_id','id','title_kaggle','original_title','tagline','belongs_to_collection','url','imdb_link',
                            'runtime','budget_kaggle','revenue','release_date_kaggle','popularity','vote_average','vote_count',
                            'genres','original_language','overview','spoken_languages','Country',
                            'production_companies','production_countries','Distributor',
                            'Producer(s)','Director','Starring','Cinematography','Editor(s)','Writer(s)','Composer(s)','Based on'
                            ]]

        # Rename columns to be consistent
        movies_df.rename({'id':'kaggle_id',
                        'title_kaggle':'title',
                        'url':'wikipedia_url',
                        'budget_kaggle':'budget',
                        'release_date_kaggle':'release_date',
                        'Country':'country',
                        'Distributor':'distributor',
                        'Producer(s)':'producers',
                        'Director':'director',
                        'Starring':'starring',
                        'Cinematography':'cinematography',
                        'Editor(s)':'editors',
                        'Writer(s)':'writers',
                        'Composer(s)':'composers',
                        'Based on':'based_on'
                        }, axis='columns', inplace=True)

    except:
        print("An error occured merging and organizing the Wikipedia and Kaggle data files, review for details")

    try:
        # use groupby to get count for each group then rename column
        rating_counts = ratings.groupby(['movieId','rating'], as_index=False).count() \
                        .rename({'userId':'count'}, axis=1) 

        # Create pivot table so that movieId is the index, the columns will be all the rating values, and the rows
        # will be the counts for each rating value.
        rating_counts = ratings.groupby(['movieId','rating'], as_index=False).count() \
                        .rename({'userId':'count'}, axis=1) \
                        .pivot(index='movieId',columns='rating', values='count')

        # prepend rating_ to each column with a list comprehension to rename columns
        rating_counts.columns = ['rating_' + str(col) for col in rating_counts.columns]
            
        # Use left merge to combine data
        movies_with_ratings_df = pd.merge(movies_df, rating_counts, left_on='kaggle_id', right_index=True, how='left')   
            
        # Fill in missing rating values with zero
        movies_with_ratings_df[rating_counts.columns] = movies_with_ratings_df[rating_counts.columns].fillna(0)
    
    except:
        print("An error occured while cleaning and merging the ratings data file, review for details")

    try:
        # Make a connection string so the database engine can connect to the database
        db_string = f"postgres://postgres:{db_password}@127.0.0.1:5432/movie_data"

        # Create the database engine
        engine = create_engine(db_string)
    except:
        print("An error occured while connecting to SQL, review for details")

    #try:
        # Remove all data from tables so new data can be entered
        #DELETE FROM movies;
        #DELETE FROM ratings;
    #except:
        #print("An error occured removing old data from SQL tables, review for details")

    try:
        # Import movie df into SQL table
        movies_df.to_sql(name='movies', con=engine)

        # Import Rating Data by breaking file into chuncks
        rows_imported = 0
        start_time = time.time()
        for data in pd.read_csv(f'{file_dir}ratings.csv', chunksize=1000000):
            print(f'importing rows {rows_imported} to {rows_imported + len(data)}...', end='')
            data.to_sql(name='ratings', con=engine, if_exists='append')
            rows_imported += len(data)
            print(f'Done. {time.time() - start_time} total seconds elapsed')

    except:
        print("An error occured while importing data to SQL, review for details")