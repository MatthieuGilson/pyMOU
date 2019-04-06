#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains additional functions useful for working with and testing
the EC estimator toolbox.

Created on Tue Nov  7 15:50:53 2017
@author: andrea
"""
from __future__ import division, print_function

import numpy as np

## GORKA: These four functions, if kept, they should go in another file.
## Leave this file only for the MOU object and its attributes. The import to
## networkx is thus neither necessary.
#def make_chain():
#    chain = nx.DiGraph()
#    chain.add_nodes_from(['X', 'Y', 'Z'])
#    chain.add_edges_from([('Y', 'Z'), ('Z', 'X')])
#    return chain
#
#def make_common_input():
#    common_drive = nx.DiGraph()
#    common_drive.add_nodes_from(['X', 'Y', 'Z'])
#    common_drive.add_edges_from([('Z', 'X'), ('Z', 'Y')])
#    return common_drive
#
#def make_full():
#    full = nx.DiGraph()
#    full.add_nodes_from(['X', 'Y', 'Z'])
#    full.add_edges_from([('X', 'Z'), ('Y', 'Z'), ('X', 'Y'), ('Z', 'Y'), ('Y', 'X'), ('Z', 'X')])
#    return full

def make_rnd_connectivity(N, density=0.2, w_min=0., w_max=0.1):
    """
    Creates a random connnectivity matrix as the element-wise product $ C' = A \otimes W$,
    where A is a binary adjacency matrix samples from Bern(density) and W is sampled from 
    a uniform random distribution between w_min and w_max.
    """
    C = w_min + (w_max - w_min) * np.random.rand(N, N)
    C[np.random.rand(N, N) > density] = 0
    C[np.eye(N, dtype=bool)] = 0
    return C
