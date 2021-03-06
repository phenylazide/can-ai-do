"""A fingerprint + random forest model.
Try to generate independent and identically distributed figerprint as decoy.
"""
import os
import sys
import json
import argparse
import numpy as np
from pathlib import Path
from tqdm import tqdm

import scipy.sparse as sp
from scipy.spatial import distance
from multiprocessing import Pool

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import DataStructs

from sklearn import metrics
from sklearn.ensemble import RandomForestClassifier

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('-i', '--index', required=True)
parser.add_argument('-j', '--json_split', required=True)
parser.add_argument(
    '-d', '--datadir', default='./v2018', help="datadir, default is ./v2018")
args = parser.parse_args()

def read_index(index_file):
    with open(index_file) as f:
        for i in f:
            if i[0] == '#': continue
            code, reso, year, pK, *others = i.split()
            yield code, float(pK)

codes = []
pKs = []
ligands = []
fps = []
datadir = Path(args.datadir)
for code, pK in tqdm(read_index(args.index)):
    # sdf = datadir / code / (code + '_ligand.sdf')
    pdb = datadir / (code + '_ligand.pdb')
    if not pdb.exists():
        continue
    # mol = Chem.MolFromPDBFile(str(pdb), removeHs=False)
    mol = Chem.MolFromPDBFile(str(pdb))
    if mol is None:
        continue
    # fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=512)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
    codes.append(code)
    pKs.append(pK)
    ligands.append(mol)
    fps.append(fp)
pKs = np.array(pKs)
print('succeed {}'.format(len(codes)))
split_index = json.load(open(args.json_split))
dataset_split = split_index['pdbbind']['general_PL']
# for seed, split in dataset_split.items():
#     train = split['splitted_ids']['train']
#     valid = split['splitted_ids']['valid']
#     test = split['splitted_ids']['test']
#     print(len(train)+len(valid) + len(test))
#     train_idx = [codes.index(i) for i in train]
#     valid_idx = [codes.index(i) for i in valid]
#     test_idx = [codes.index(i) for i in test]
for i in range(3):
    seed = i
    N = len(codes)
    perm = np.random.permutation(N)
    train_idx = perm[:int(N*0.8)]
    valid_idx = perm[int(N*0.8):int(N*0.9)]
    test_idx = perm[int(N*0.9):]
    train_fps = [fps[i] for i in train_idx]
    test_pKs = [pKs[i] for i in test_idx]
    pred_pKs = []
    for i in test_idx:
        simi = DataStructs.BulkTanimotoSimilarity(fps[i], train_fps)
        # most_simi_idx = np.argmax(simi)
        # pred_pKs.append(pKs[most_simi_idx])
        most_simi_three = np.argsort(simi)[-3:]
        pred_pKs.append(np.mean(pKs[most_simi_three]))
    r2 = np.corrcoef(test_pKs, pred_pKs)[0,1] ** 2
    print('pdbbind general_PL seed {} r2: {}'.format(seed, r2))
