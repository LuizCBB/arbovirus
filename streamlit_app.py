from tqdm import tqdm
import streamlit as st
import pickle
import screed
from scipy.special import softmax
import pandas as pd
import mmh3

alphabet = ["A", "C", "T", "G"]
ksize = 11
n = 200

def jaccard_similarity(a, b):
    a = set(a)
    b = set(b)

    intersection = len(a.intersection(b))
    n_a = len(a)
    n_b = len(b)

    return intersection / (n_a + n_b - intersection)

def clear_sequence(sequence):
    sequence = sequence.upper()
    clear_seq = ""
    for i in sequence:
        if i in alphabet:
            clear_seq += i
    return clear_seq

def build_kmers(sequence):
    sequence = clear_sequence(sequence)
    kmers = []
    n_kmers = len(sequence) - ksize + 1

    for i in range(n_kmers):
        kmer = sequence[i:i + ksize]
        kmers.append(kmer)

    return kmers


def hash_kmer(kmer):
    # calculate the reverse complement
    rc_kmer = screed.rc(kmer)

    # determine whether original k-mer or reverse complement is lesser
    if kmer < rc_kmer:
        canonical_kmer = kmer
    else:
        canonical_kmer = rc_kmer

    # calculate murmurhash using a hash seed of 42
    hash = mmh3.hash64(canonical_kmer, 42)[0]
    if hash < 0: hash += 2**64

    # done
    return hash


def hash_kmers(kmers):
    hashes = []
    for kmer in kmers:
        hashes.append(hash_kmer(kmer))
    return hashes



def subsample_modulo(kmers, n):
    hashed_kmers = hash_kmers(kmers)
    hashed_kmers.sort()
    
    if( len(hashed_kmers) <= n ):
        keep = hashed_kmers
    else:
        keep = []
        for i in range(n):
            keep.append(hashed_kmers[i])
            
    return keep


def step1(query_sequences):
    progress_text = "Processing the query sequences into k-mers (k = " + str(ksize) + ") ... "
    print(progress_text)
    
    kmers_list_query = []
    counter = 0
    for i in tqdm(query_sequences):
        counter += 1
        my_bar1.progress(round( (counter/len(query_sequences))*100 ), text=progress_text + str(counter) + " of " + str(len(query_sequences)))
        kmers_list_query.append( build_kmers(i) )
        
    return kmers_list_query

def step2(kmers_list_query):
    progress_text = "Sampling the k-mer data ..."
    print(progress_text)

    kmers_hash_query_sampled = []
    counter = 0
    for kmers in tqdm(kmers_list_query):
        counter += 1
        my_bar2.progress(round( (counter/len(kmers_list_query))*100 ), text=progress_text + str(counter) + " of " + str(len(kmers_list_query)))
        kmers_hash_query_sampled.append(subsample_modulo(kmers, n))

    return kmers_hash_query_sampled

def step3(kmers_hash_query_sampled, kmers_hash_db_sampled):
    progress_text = "Calculating the jaccard similarity between the sequences using their respective kmer data ..."
    print(progress_text)
    
    matrix_query = []
    counter = 0
    for i in tqdm(range(len(kmers_hash_query_sampled))):
        counter += 1
        my_bar3.progress(round( (counter/len(kmers_hash_query_sampled))*100 ), text=progress_text + str(counter) + " of " + str(len(kmers_hash_query_sampled)))
        js = []
        for j in range(len(kmers_hash_db_sampled)):
            js.append( jaccard_similarity(kmers_hash_query_sampled[i], kmers_hash_db_sampled[j]) * 100)
        matrix_query.append(js)

    return matrix_query

#########################################################################################################################################


with open("model_RLM_dataset_treino_k11.pkl", 'rb') as f:
    model = pickle.load(f)
f.close()

with open("matriz_dataset_treino_k11_kmers_hash_sampled.pkl", "rb") as input_file:
    kmers_hash_db_sampled = pickle.load(input_file)    
input_file.close()

labels_model = ['ASV_1000', 'Chikungunya_1000', 'Dengue1_1000', 'Dengue2_1000',
 'Dengue3_1000', 'Dengue4_1000', 'Eastern_equine_encephalitis_997',
 'Japanese_encephalitis_1000', 'La_Crosse_198', 'Mayaro_138', 'Oropouche_382',
 'Rift_Valley_fever_1000' ,'Saint_Louis_encephalitis_256', 'Sindbis_530',
 'Usutu_virus_982', 'West_Nile_1000', 'Western_equine_encephalitis_124',
 'Yellow_fever_1000', 'Zika_1000'] 
 
 
st.header('Deploy do modelo de regressão logística multinomial')
sequences_area = st.text_area(
    "Paste in your sequence (fasta format) or use the example", height = 300
    )
    
query_sequences = []
query_labels = [] 
   
br = st.button("Run")
if br:
    temp = open("temp.fas", "w")
    temp.write(sequences_area)
    temp.close()
    
    for record in screed.open("temp.fas"):
        name = record.name
        sequence = record.sequence
        
        
        query_labels.append(name)
        query_sequences.append(sequence)
        
    n_queries = len(query_sequences)
    

    
    my_bar1 = st.progress(0, text="")
    kmers_list_query = step1(query_sequences)

    my_bar2 = st.progress(0, text="")
    kmers_hash_query_sampled = step2(kmers_list_query)

    my_bar3 = st.progress(0, text="")
    matrix = step3(kmers_hash_query_sampled, kmers_hash_db_sampled)
    
    predicted_class = []
    query_name = []
            
    counter_label = 0
    counter = n_queries
    while (counter > 0):
                   
        query = matrix[-(counter)]
                    
            
        yhat = model.predict([query])
        prob = softmax( model.predict_proba([query])[0] )*100
            
                    
        
                    
        if( (max(prob) - min(prob)) < 0):
                
            predicted_class.append("Other")
            query_name.append(query_labels[counter_label])
                    
        else:
                
            predicted_class.append(yhat[0]) 
            query_name.append(query_labels[counter_label])
            
                    
        counter -= 1
        counter_label += 1 
            
    d = {'Query name': query_name, 'Predicted class': predicted_class }
    df = pd.DataFrame(data=d,index=None)
            
    st.table(df)
    






    
