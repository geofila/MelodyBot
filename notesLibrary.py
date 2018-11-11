from music21 import *
import mido
import time
import sys
import numpy as np
from pathlib import Path
from tqdm import tqdm

def decode_categorical(music):
    ''' Συνάρτηση που αποκωδικοποιεί την μουσική όπως με την μορφή που αποθηκευέται στα αρχεια
        Είσοδος: μια νότα κωδικοποιημένη σαν string της μορφής 'Pitch|Value'
        Έξοδος: το Pitch και η αξία της νότας εισόδου
    '''
    notes, durations = [], []
    for i in music:
        raw = categorical_to_notes[i]
        note, duration = raw.split("|")
        notes.append(int(note))
        durations.append(float(duration))
    return notes, durations

def print_progress(c, msg = 'Note: '):
    text = '\r' + msg + " %i"
    sys.stdout.write(text % c)
    sys.stdout.flush()

def play_song(music, start):
    '''
    Είσοδος: μια λίστα με categorical νοτες (σαν integer)
    'Εξοδος: None, απλά παίζεται ελνα κομμάτι από της έξοδο της συσκευής
    '''
    notes_music, dur_music = decode_categorical(music)
    ticksPerQuarter = tpq[start]
    t = tempos[start]
    counter = 0
    start_time = time.time()
    defaults.ticksPerQuarter = ticksPerQuarter
    for n, d in zip(notes_music, dur_music):
        ticks = midi.translate.durationToMidi(duration.Duration(quarterLength = d))
        real_time = mido.tick2second(ticks, ticksPerQuarter , t)
        time.sleep(real_time)
        msg = mido.Message(type = 'note_on', note = n, velocity = 127)
        port.send(msg)
        counter += 1
        print_progress(counter)

def get_train_size(inp_size, batch_size):
    for i in range (inp_size, 0, -1):
        if i % batch_size == 0:
            return i

def create_dataset(notes, seq_length_in, seq_length_out, batch_size):
    size = get_train_size(len(notes) - seq_length_in - seq_length_out, batch_size)
    inp, outp, targ = [], [], []
    for i in tqdm(range (size)):
        inp.append(notes[i: i + seq_length_in])
        outp.append([0] + notes[i + seq_length_in: i + seq_length_in + seq_length_out - 1])
        targ.append(notes[i + seq_length_in: i + seq_length_in + seq_length_out])
    inp = np.array(inp)
    outp = np.array(outp)
    targ = np.array(targ).reshape((-1, seq_length_out, 1))
    return inp, outp, targ



notes = []
tempos = []
tpq = []
songs_lengths = [0]
n = []
dur = []
def components(d):
    ret = []
    try:
        ret = d.components
    except:
        ret = d.Duration('2048th').components
    finally:
        return ret

def decode(path, states_save = True):
    '''Η συνάρτηση που αποκοδηκοποιεί τα τραγούδια. Τα μετατρέπει από .mid αρχεία σε μια λίστα με νότες τις μορφής 'Pitch|Value',
        Η μεταβλητή save_states κάνει εξικονόμηση των καταστάσεων των αξιών. Αν είναι false ο χρόνος εκτέλεσης μειώνεται
        πάρα πολύ αλλα αυξάνονται οι συνολικές διαφορετικες καταστάσεις του χρόνου.
        Είσοδος: ένας φάκελος που περιέχει ΜΌΝΟ .mid αρχεία
        Έξοδος: None, απλά γεμίζει τις λίστες που ορίστικαν παραπάνω
    '''
        path = Path(path)
        l = list (path.iterdir())
        acc= 0
        for file in tqdm(l):
            mf = midi.MidiFile()
            mf.open(file)
            mf.read()

            tpq_v = mf.ticksPerQuarterNote    #values of tpq for storing that multiple times in tpq list
            defaults.ticksPerQuarter = tpq_v
            mf.close()

            last_time = 0
            for track in mf.tracks:
                events = track.events
                t = 0
                for e in events:
                    if e.type is 'SET_TEMPO':
                        tempo = midi.getNumber(e.data, len(e.data))[0]
                    if e.isDeltaTime and (e.time is not None):
                        t += e.time
                    elif ( e.isNoteOn and ( e.pitch is not None)):
                        d = midi.translate.midiToDuration(t - last_time, ticksPerQuarter = tpq_v)
                        if states_save:
                            for i in components(d):
                                notes.append(str(e.pitch) +  "|" + str(i[2]))
                                n.append(e.pitch)
                                dur.append(i[2])
                                tempos.append(tempo)
                                tpq.append(tpq_v)
                        else:
                            notes.append(str(e.pitch) +  "|" + str(d.quarterLength))
                            n.append(e.pitch)
                            dur.append(d.quarterLength)
                            tempos.append(tempo)
                            tpq.append(tpq_v)

                        last_time= t
            songs_lengths.append(len(notes))
            acc += 1
