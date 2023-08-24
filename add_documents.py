import os
import hashlib
from tika import parser
import requests
import time
from multiprocessing import Pool, Manager
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from config import solr_cores, solr_url, folders

# Funzione per ricaricare un core in Solr
def reload_core(core_name):
    reload_url = f"{solr_url}/admin/cores?action=RELOAD&core={core_name}"
    response = requests.get(reload_url)
    if response.status_code == 200:
        print(f"Core '{core_name}' ricaricato con successo")
    else:
        print(f"Errore durante la ricarica del core '{core_name}': {response.text}")

# Funzione per generare l'ID del documento basato sul nome del file, il path e la cartella
def generate_document_id(file_name, file_path, folder):
    input_string = f"{file_name}:{file_path}:{folder}"
    hashed = hashlib.sha256(input_string.encode()).hexdigest()
    return hashed

# Funzione per indicizzare un documento in un core specifico
def index_document(document, core_name):
    # URL per l'aggiunta di documenti in Solr
    add_url = f"{solr_url}/{core_name}/update/json/docs"

    # Numero massimo di tentativi di connessione in caso di fallimento
    max_retries = 3

    for retry in range(max_retries):
        try:
            # Indicizzazione del documento nel core specificato
            response = requests.post(add_url, json=document)
            if response.status_code == 200:
                print(f"Documento indicizzato nel core {core_name}")
                break  # Esci dal loop se la richiesta ha successo
            else:
                print(f"Errore durante l'indicizzazione del documento nel core {core_name}")
                break  # Esci dal loop anche se la richiesta ha fallito

        except requests.exceptions.RequestException as e:
            # Gestisci l'errore di connessione
            logging.error(f"Tentativo {retry + 1} di connessione a Solr fallito: {e}")
            if retry < max_retries - 1:
                # Aspetta 1 secondo prima di ritentare
                time.sleep(1)
                continue
            else:
                # Se tutti i tentativi hanno fallito, esci dal loop
                break

        except Exception as e:
            # Gestisci altri errori
            logging.error(f"Errore durante l'indicizzazione del documento nel core {core_name}: {e}")
            break

# Funzione per scorrere e poi indicizzare i documenti nelle cartelle
def index_folder_documents(folder, core_name, queue):
    folder_path = os.path.abspath(folder)

    for root, dirs, files in os.walk(folder_path):
        # Escludi le cartelle nascoste
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file_name in files:
            if file_name.startswith('.'):
                continue

            file_path = os.path.join(root, file_name)
            document_id = generate_document_id(os.path.splitext(file_name)[0], file_path, core_name)

            # Verifica se il documento è già indicizzato su Solr
            check_url = f"{solr_url}/{core_name}/select?q=id:{document_id}"
            response = requests.get(check_url)
            if response.status_code == 200 and response.json()['response']['numFound'] > 0:
                print(f"Il documento '{file_path}' è già indicizzato su Solr.")
            else:
                # Estrazione del contenuto testuale del documento utilizzando Apache Tika
                print("Parsing...")
                parsed_data = parser.from_file(file_path)
                text_content = parsed_data['content']

                # Creazione del documento da indicizzare
                document = {
                    'id': document_id,
                    'title': file_name,  # Inserisci il titolo come campo separato
                    'content': text_content,  # Inserisci il contenuto come campo separato
                    'path': file_path,  # Inserisci il percorso come campo separato
                }

                # Aggiungi il documento alla coda condivisa
                queue.put((document, core_name))

    print(f"Cartella '{folder}' elaborata.")

# Funzione per indicizzare i documenti nelle cartelle
def index_documents():
    manager = Manager()
    document_queue = manager.Queue()  # Crea la coda condivisa

    # Puoi ridurre il numero di processi nel Pool per diminuire il carico sul server Solr.
    with Pool(processes=2) as pool:
        # Avvia i processi per l'indicizzazione delle cartelle
        for folder, core_name in zip(folders.values(), solr_cores):
            pool.apply_async(index_folder_documents, args=(folder, core_name, document_queue))

        # Attendere che tutti i processi abbiano completato il lavoro
        pool.close()
        pool.join()

    # Introduce un ritardo 
    time.sleep(1)

    # Recupera i documenti dalla coda condivisa e indicizzali in batch
    batch_documents = []
    while not document_queue.empty():
        document, core_name = document_queue.get()
        batch_documents.append((document, core_name))

    # Puoi aumentare il numero di workers nel ThreadPoolExecutor per sfruttare un maggiore parallelismo.
    # Tieni conto del numero di core disponibili sulla tua macchina.
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Avvia i processi per l'indicizzazione delle cartelle
        futures = [executor.submit(index_document, doc, core_name) for doc, core_name in batch_documents]

        # Attendere che tutti i futuri siano completati
        for future in as_completed(futures):
            try:
                future.result()  # Recupera il risultato del futuro (se ci sono eccezioni, vengono propagate qui)
            except Exception as e:
                logging.error(f"Errore durante l'indicizzazione: {e}")

    print(f"Indicizzati {len(batch_documents)} documenti in batch.")

    # Ricarica tutti i core
    for core_name in solr_cores:
        reload_core(core_name)

# Funzione per eseguire l'indicizzazione ogni minuto
def run_indexing():
    print("Esecuzione dell'indicizzazione dei documenti...")
    index_documents()
    print("Indicizzazione completata.")

# Loop principale per eseguire le attività programmate
def indexing_scheduler():
    while True:
        run_indexing()

        #Tempo per ogni ciclo di indicizzazione
        time.sleep(3600) 

if __name__ == "__main__":
    indexing_thread = threading.Thread(target=indexing_scheduler)
    indexing_thread.start()
    indexing_thread.join()