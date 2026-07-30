"""Routes for Inventory API."""
from flask import Blueprint, request, jsonify
from app.models import db, Movie

bp = Blueprint('movies', __name__)

@bp.route('/api/movies', methods=['GET'])
def get_movies():
    title_query = request.args.get('title')
    if title_query:
        # Strip brackets if passed in the format [name]
        if title_query.startswith('[') and title_query.endswith(']'):
            title_query = title_query[1:-1]
        # Perform a case-insensitive search matching the query substring
        movies = Movie.query.filter(Movie.title.ilike(f'%{title_query}%')).all()
    else:
        movies = Movie.query.all()
    return jsonify([movie.to_dict() for movie in movies]), 200

@bp.route('/api/movies/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"error": "Movie not found"}), 404
    return jsonify(movie.to_dict()), 200

@bp.route('/api/movies', methods=['POST'])
def create_movie():
    data = request.get_json(silent=True) or {}
    title = data.get('title')
    description = data.get('description')
    
    if not title:
        return jsonify({"error": "Missing required field: title"}), 400
        
    new_movie = Movie(title=title, description=description)
    db.session.add(new_movie)
    db.session.commit()
    
    return jsonify(new_movie.to_dict()), 201

@bp.route('/api/movies/<int:movie_id>', methods=['PUT'])
def update_movie(movie_id):
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"error": "Movie not found"}), 404
        
    data = request.get_json(silent=True) or {}
    
    if 'title' in data:
        movie.title = data['title']
    if 'description' in data:
        movie.description = data['description']
        
    db.session.commit()
    return jsonify(movie.to_dict()), 200

@bp.route('/api/movies', methods=['DELETE'])
def delete_all_movies():
    try:
        num_deleted = db.session.query(Movie).delete()
        db.session.commit()
        return jsonify({"message": f"Successfully deleted all movies. Total: {num_deleted}"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/api/movies/<int:movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    movie = Movie.query.get(movie_id)
    if not movie:
        return jsonify({"error": "Movie not found"}), 404
        
    db.session.delete(movie)
    db.session.commit()
    return jsonify({"message": f"Movie with ID {movie_id} deleted successfully"}), 200
