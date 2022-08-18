#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from audioop import add
from dataclasses import dataclass
from email.policy import default
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, abort
from flask_moment import Moment
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from datetime import datetime
import sys
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from models import db, Venue, Artist, Show
db.init_app(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  latest_venues = db.session.query(Venue.name).order_by(Venue.id.desc()).limit(10).all()
  latest_artist = db.session.query(Artist.name).order_by(Artist.id.desc()).limit(10).all()
  latest_venues_names = []
  latest_artist_names = []
  for venue in latest_venues:
    latest_venues_names.append(venue[0])
  for artist in latest_artist:
    latest_artist_names.append(artist[0])
  
  data = {
    'latest_artist': latest_artist_names,
    'latest_venues': latest_venues_names
  }
  return render_template('pages/home.html', data=data)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  unique_cities_and_state = set(db.session.query(Venue.city, Venue.state).all())
  for value in unique_cities_and_state:
    obj = {}
    city = value[0]
    state = value[1]
    venues_in_citystate = Venue.query.filter(Venue.city == city and Venue.state == state).all()
    
    venues = []
    for venue in venues_in_citystate:
      venue_object = {
        'id': venue.id,
        'name': venue.name,
        'num_upcoming_shows': len(get_venue_upcoming_shows(venue))
      }
      venues.append(venue_object)
    obj['city'] = city
    obj['state'] = state
    obj['venues'] = venues
    
    data.append(obj)
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  search_term = request.form['search_term'].lower().strip()
  venues_in_search = db.session.query(Venue).filter(db.func.lower(Venue.name).like('%' + search_term + '%') | db.func.lower(Venue.city).like('%' + search_term + '%') | db.func.lower(Venue.state).like('%' + search_term + '%')).all()
  data = []
  for venue in venues_in_search:
    obj = {
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_shows': len(get_venue_upcoming_shows(venue))
    }
    data.append(obj)
  
  response = {
    'count': len(venues_in_search),
    'data': data
  }
  
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)
  all_past_shows = get_venue_past_shows(venue)
  all_upcoming_shows = get_venue_upcoming_shows(venue)
  
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres.split(","),
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": get_artist_data_in_shows(all_past_shows),
    "upcoming_shows": get_artist_data_in_shows(all_upcoming_shows),
    "past_shows_count": len(get_venue_past_shows(venue)),
    "upcoming_shows_count": len(get_venue_upcoming_shows(venue))
  }
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm(request.form)
  if form.validate():
    try:
      venue = Venue(
        name=form.name.data,
        city=form.city.data,
        state=form.state.data,
        address=form.address.data,
        phone=form.phone.data,
        genres=",".join(form.genres.data),
        facebook_link=form.facebook_link.data,
        image_link=form.image_link.data,
        website = form.website_link.data,
        seeking_talent = form.seeking_talent.data,
        seeking_description = form.seeking_description.data
      )
      db.session.add(venue)
      db.session.commit()
      flash('Venue: {0} created successfully'.format(venue.name))
    except Exception as err:
      flash('An error occurred creating the Venue: {0}. Error: {1}'.format(venue.name, err))
      db.session.rollback()
    finally:
      db.session.close()
      return redirect(url_for('index')) 
  else:
      return render_template('forms/new_venue.html', form=form)
      
    

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  error = False
  try:
    Show.query.filter_by(venue_id=venue_id).delete()
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    db.session.rollback()
    error = True
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    return render_template('pages/home.html'), 200
  else:
    abort(500)

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = []
  all_artists = Artist.query.all()
  for artist in all_artists:
    obj = {
      'id': artist.id,
      'name': artist.name
    }
    data.append(obj)
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_term = request.form['search_term'].lower().strip()
  artists_in_search = db.session.query(Artist).filter(db.func.lower(Artist.name).like('%' + search_term + '%') | db.func.lower(Artist.city).like('%' + search_term + '%') | db.func.lower(Artist.state).like('%' + search_term + '%')).all()
  data = []
  for artist in artists_in_search:
    obj = {
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_shows': len(get_venue_upcoming_shows(artist))
    }
    data.append(obj)
  
  response = {
    'count': len(artists_in_search),
    'data': data
  }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  artist = Artist.query.get(artist_id)
  all_past_shows = get_artist_past_shows(artist)
  all_upcoming_shows = get_artist_upcoming_shows(artist)
  
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres.split(','),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": get_venue_data_in_shows(all_past_shows),
    "upcoming_shows": get_venue_data_in_shows(all_upcoming_shows),
    "past_shows_count": len(get_artist_past_shows(artist)),
    "upcoming_shows_count": len(get_artist_upcoming_shows(artist))
  }
  
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  selected_artist = Artist.query.get(artist_id)
  artist={
    "id": selected_artist.id,
    "name": selected_artist.name,
    "genres": selected_artist.genres.split(','),
    "city": selected_artist.city,
    "state": selected_artist.state,
    "phone": selected_artist.phone,
    "website": selected_artist.website,
    "facebook_link": selected_artist.facebook_link,
    "seeking_venue": selected_artist.seeking_venue,
    "seeking_description": selected_artist.seeking_description,
    "image_link": selected_artist.image_link
  }
  
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  form = ArtistForm(request.form)
  if form.validate():
    try:
      artist = Artist.query.get(artist_id)
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.genres = ",".join(form.genres.data)
      artist.facebook_link = form.facebook_link.data
      artist.image_link = form.image_link.data
      artist.website = form.website_link.data
      artist.seeking_venue = form.seeking_venue.data
      artist.seeking_description = form.seeking_description.data

      db.session.commit()
      flash('Artist: {0} updated successfully'.format(artist.name))
    except Exception as err:
      flash('An error occurred while editing the Artist: {0}. Error: {1}'.format(artist.name, err))
      db.session.rollback()
    finally:
      db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))
  else:
    flash('Input Error: Check the values you enterred')
    return redirect(url_for('edit_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  selected_venue = Venue.query.get(venue_id)
  venue={
    "id": selected_venue.id,
    "name": selected_venue.name,
    "genres": selected_venue.genres.split(','),
    "address": selected_venue.address,
    "city": selected_venue.city,
    "state": selected_venue.state,
    "phone": selected_venue.phone,
    "website": selected_venue.website,
    "facebook_link": selected_venue.facebook_link,
    "seeking_talent": selected_venue.seeking_talent,
    "seeking_description": selected_venue.seeking_description,
    "image_link": selected_venue.image_link
  }
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm(request.form)
  if form.validate():
    try:
      venue = Venue.query.get(venue_id)
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.address = form.address.data
      venue.phone = form.phone.data
      venue.genres = ",".join(form.genres.data)
      venue.facebook_link = form.facebook_link.data
      venue.image_link = form.image_link.data
      venue.website = form.website_link.data
      venue.seeking_talent = form.seeking_talent.data
      venue.seeking_description = form.seeking_description.data

      db.session.commit()
      flash('Venue: {0} updated successfully'.format(venue.name))
    except Exception as err:
      flash('An error occurred while editing the Venue: {0}. Error: {1}'.format(venue.name, err))
      db.session.rollback()
    finally:
      db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))
  else:
    flash('Input Error: Check the values you enterred')
    return redirect(url_for('edit_venue', venue_id=venue_id))
    

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  form = ArtistForm(request.form)
  if form.validate():
    try:
      artist = Artist(
          name=form.name.data,
          city=form.city.data,
          state=form.state.data,
          phone=form.phone.data,
          genres=",".join(form.genres.data),
          facebook_link=form.facebook_link.data,
          image_link=form.image_link.data,
          website = form.website_link.data,
          seeking_venue = form.seeking_venue.data,
          seeking_description = form.seeking_description.data
      )
      db.session.add(artist)
      db.session.commit()
      flash('Venue: {0} created successfully'.format(artist.name))
    except Exception as err:
      flash('An error occurred creating the Venue: {0}. Error: {1}'.format(artist.name, err))
      db.session.rollback()
    finally:
      db.session.close()
    return redirect(url_for('index'))
  else:
    return render_template('forms/new_artist.html', form=form)
    

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  
  details = db.session.query(Show, Artist, Venue).join(Artist).join(Venue).all()
  data = []
  for detail in details:
    obj = {}
    show = detail[0]
    artist = detail[1]
    venue = detail[2]
  
    obj['venue_id'] = venue.id
    obj['venue_name'] = venue.name
    obj['artist_id'] = artist.id
    obj['artist_name'] = artist.name
    obj['artist_image_link'] = artist.image_link
    obj['start_time'] = str(show.start_time)
    
    data.append(obj)
    
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  
  try:
    form = ShowForm(request.form)
    show = Show(
        artist_id = form.artist_id.data,
        venue_id = form.venue_id.data,
        start_time = form.start_time.data 
    )
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')  
  except Exception as err:
    flash('An error occurred. Show could not be listed.')
    db.session.rollback()
  finally:
    db.session.close()
  
  return redirect(url_for('index'))

def get_venue_upcoming_shows(venue):
  upcoming_shows = db.session.query(Show).join(Artist).filter(Show.venue_id==venue.id).filter(Show.start_time > datetime.now()).all()
  return upcoming_shows
def get_venue_past_shows(venue):
  past_shows = db.session.query(Show).join(Artist).filter(Show.venue_id==venue.id).filter(Show.start_time < datetime.now()).all()
  return past_shows
def get_artist_upcoming_shows(artist):
  upcoming_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist.id).filter(Show.start_time > datetime.now()).all()
  return upcoming_shows
def get_artist_past_shows(artist):
  past_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist.id).filter(Show.start_time < datetime.now()).all()
  return past_shows
def get_artist_data_in_shows(shows):
  shows_list = []
  for show in shows:
    obj = {
      'artist_id': show.artist_id,
      'start_time': str(show.start_time),
      'artist_image_link': Artist.query.get(show.artist_id).name,
      'artist_name': Artist.query.get(show.artist_id).image_link
    }
    shows_list.append(obj)
  return shows_list
def get_venue_data_in_shows(shows):
  shows_list = []
  for show in shows:
    obj = {
      'venue_id': show.venue_id,
      'start_time': str(show.start_time),
      'venue_image_link': Venue.query.get(show.venue_id).name,
      'venue_name': Venue.query.get(show.venue_id).image_link
    }
    shows_list.append(obj)
  return shows_list


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
