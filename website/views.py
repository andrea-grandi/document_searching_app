from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note
from . import db
import json
import requests
from flask import send_file, render_template, make_response
from config import solr_cores

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note = request.form.get('note')#Gets the note from the HTML 

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
            db.session.add(new_note) #adding the note to the database 
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)

# Funzione per cercare documenti in Solr
@views.route('/search', methods=['GET', 'POST'])
@login_required
def search_documents():
    if request.method == 'POST':
        query = request.form.get('query', '')

        # solr_url = 'http://localhost:8983/solr'  # URL di Solr

        # Parametri comuni per la ricerca in tutti i core
        params = {
            'q': query,
            'rows': 10,
            'fl': '_src_'  # Recupera il campo _src_
        }

        results = []  # Lista per memorizzare i risultati da tutti i core

        for core in solr_cores:
            # URL per la ricerca nel core corrente
            url = f'{solr_url}/{core}/select'

            # Esegui la richiesta HTTP
            response = requests.get(url, params=params)
            response_json = response.json()

            # Estrai i risultati dalla risposta JSON
            core_results = response_json['response']['docs']

            unique_paths = set()  # Set per tenere traccia dei path unici

            # Aggiorna i risultati con il titolo e il percorso dal campo _src_
            for result in core_results:
                src_data = result.get('_src_', {})  # Recupera il campo _src_

                if isinstance(src_data, str):
                    # Converte la stringa JSON in un oggetto Python
                    try:
                        src_data = json.loads(src_data)
                    except json.JSONDecodeError:
                        # Gestione dell'errore se la stringa JSON non è valida
                        src_data = {}

                title = src_data.get('title', '')  # Estrai il titolo dal campo _src_
                path = src_data.get('path', '')  # Estrai il percorso dal campo _src_

                # Verifica se sia il titolo che il percorso sono presenti
                if title and path:
                    # Verifica se il path è già stato aggiunto
                    if path not in unique_paths:
                        unique_paths.add(path)  # Aggiungi il path al set dei path unici
                        updated_result = {'filename': title, 'path': path, 'core': core}
                        results.append(updated_result)

        user = current_user
        return render_template('results.html', results=results, user=user)
    else:
        return redirect(url_for('views.home'))
    
@views.route('/view_file', methods=['GET'])
@login_required
def view_file():
    path = request.args.get('path')
    try:
        return send_file(path, as_attachment=False)
    except FileNotFoundError:
        return render_template('exceptions.html', error_message='File not found: il file potrebbe essere stato eliminato dalla cartella ma non ancora da solr')

@views.route('/delete-note', methods=['POST'])
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note.user_id == current_user.id:
        db.session.delete(note)
        db.session.commit()

    return jsonify({})


