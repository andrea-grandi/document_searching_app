# --- File di configurazione --- #

# Core 
solr_cores = ['study', 'work', 'backup']

# URL del server solr
solr_url = 'http://localhost:8983/solr' 

# Cartelle da indicizzare in base al core
folders = {'study': 'path/to/study', 
           'work': 'path/to/work', 
           'backup': 'path/to/backup'}