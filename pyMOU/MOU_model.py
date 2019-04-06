#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright 2019 Andrea Insabato, Matthieu Gilson, Gorka Zamora-López

This code is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 2.

Utility functions and classes to deal with construction, simulation and estimation for the multivariate Ornstein-Uhlenbeck (MOU) process.
"""

import numpy as np
# import networkx as nx
import scipy.linalg as spl
import scipy.stats as stt
from sklearn.base import BaseEstimator
# import matplotlib.pyplot as pp
# from matplotlib.gridspec import GridSpec


###############################################################################
class MOU(BaseEstimator):
    """
    Description of the class and a summary of its parameters, attributes and
    methods.

    Parameters
    ----------
    n_nodes : integer
        Number of nodes in the network.
    J : ndarray of rank-2
        Jacobian matrix between the nodes. The diagonal corresponds to a vector
        of time constants. For off-diagonal elements, the first dimension 
        corresponds to target nodes and the second dimension to source nodes 
        (J_ij is from j to i).
    mu : ndarray of rank-1
        Mean vector of the inputs to the nodes.
    Sigma : ndarray of rank-2
        Covariance matrix of the inputs to the nodes (multivariate Wiener process).

    Methods
    -------
    get_C : Returns the connectivity matrix (off-diagonal elements of the
        Jacobian).

    get_tau_x : Returns the time constant (related to the diagonal of the
        Jacobian)

    fit : Fit the model to a time series (time x nodes). The previous parameters
        (connectivity, etc.) are erased.

    fit_LO : Fit method relying on Lyapunov optimization (gradient descent).

    fit_moments : Fit method with maximum likelihood.

    score : Returns the goodness of fit after the optimization.
    
    simulate : Simulate the activity of the MOU process determined by J, mu and
        Sigma.    
    """

    def __init__(self, C=None, tau_x=1.0, mu=0.0, Sigma=None,
                random_state=None):
        """Initialize self. See help(MOU) for further information.
        The reason for separating the diagonal and off-diagonal elements in
        the Jacobian comes from focusing on the connectivity matrix as a graph.
        """

        # SECURITY CHECKS AND ARRANGEMENTS FOR THE PARAMETERS
        # Construct Jacobian
        if C is None:
            # 10 nodes by default
            self.n_nodes = 10
            # unconnected network
            C_tmp = np.zeros([self.n_nodes, self.n_nodes], dtype=np.float)
        elif type(C) == np.ndarray:
            if (not C.ndim==2) or (not C.shape[0] == C.shape[1]):
                raise TypeError("""Argument C in MOU constructor must be square 
                                matrix (2D).""")
            self.n_nodes = C.shape[0]
            C_tmp = C
        else:
            raise TypeError("""Only matrix accepted for argument C in MOU 
                            constructor.""")

        if np.isscalar(tau_x):
            if tau_x <= 0:
                raise ValueError("""Scalar argument tau_x in MOU constructor must 
                                be negative.""")
            else:
                tau_x_tmp = np.ones(self.n_nodes) / tau_x
        elif type(tau_x) == np.ndarray:
            if (not tau_x.ndim==1) or (not tau_x.shape[0] == self.n_nodes):
                raise TypeError("""Vector argument tau_x in MOU constructor must
                                be of same size as diagonal of C.""")
                tau_x_tmp = np.copy(tau_x)
        else:
            raise TypeError("""Only scalar value or vector accepted for argument
                            tau_x in MOU constructor.""")

        self.J = -np.eye(self.n_nodes) / tau_x_tmp + C_tmp
        if np.any(np.linalg.eigvals(self.J)>0):
            print("""The constructed MOU process has a Jacobian with negative 
                  eigenvalues, corresponding to unstable dynamics.""")

        # Inputs
        if np.isscalar(mu):
            self.mu = mu
        elif type(mu) == np.ndarray:
            if (not mu.ndim==1) or (not mu.shape[0] == self.n_nodes):
                raise TypeError("""Vector argument mu in MOU constructor must be 
                                of same size as diagonal of C.""")
            self.mu = mu
        else:
            raise TypeError("""Only scalar value or vector accepted for argument 
                            tau_x in MOU constructor.""")

        if Sigma is None:
            # uniform unit variance by default
            self.Sigma = np.eye(self.n_nodes, dtype=np.float)
#            self.Sigma = 0.5 + 0.5 * np.random.rand(self.n_nodes) * np.eye(self.n_nodes, dtype=np.float)
        elif np.isscalar(Sigma):
            if not (Sigma>0):
                raise TypeError("""Scalar argument Sigma in MOU constructor must 
                                be non-negative (akin to variance).""")
            self.Sigma = np.eye(self.n_nodes, dtype=np.float)
        elif type(Sigma) == np.ndarray:
            if (not Sigma.ndim==2) or (not Sigma.shape[0] == Sigma.shape[1]) \
                                   or (not Sigma.shape[0] == self.n_nodes):
                raise TypeError("""Matrix argument Sigma in MOU constructor must
                                be square and of same size as C.""")
            if (not Sigma == Sigma.T) or np.any(np.linalg.eigvals(Sigma)<0):
                raise ValueError("""Matrix argument Sigma in MOU constructor must 
                                 be positive semidefinite (hence symmetric).""")
            self.Sigma = Sigma
        else:
            raise TypeError("""Only scalar value or matrix accepted for argument
                            Sigma in MOU constructor.""")

        # Set seed for reproducibility
        if random_state is not None:
            np.random.seed(random_state)


    # METHODS FOR CLASS MOU ###################################################

    def get_C(self):
        """
        Returns
        -------
        C : ndarray of rank 2
            The connectivity matrix corresponding to the off-diagonal elements 
            of the Jacobian. The first dimension corresponds to target nodes 
            and the second dimension to source nodes (C_ij is from j to i).
        """
        C = np.copy(self.J)
        C[np.eye(self.n_nodes, dtype=np.bool)] = 0
        return C

    def get_tau_x(self):
        """
        Returns
        -------
        tau_x : ndarray of rank 1
            Time constants corresponding to the inverse opposite of the diagonal
            elements of the Jacobian.
        """
        tau_x = -1.0 / self.J.diagonal()
        return tau_x

    def fit(self, X, y=None, method='lyapunov', **kwargs):
        """
        Generic fit method to call the adequate specific method.

        Parameters
        ----------
        X : ndarray
            The timeseries data of the system to estimate, of shape:
            T (time points) x n_nodes (numer of variables, e.g. number of ROIs).
        y : (for compatibility, not used here).
        method : string (optional)
            Set the optimization method; should be 'lyapunov' or 'moments'.

        Returns
        -------
        J : ndarray of rank 2
            The estimated Jacobian. Shape [n_nodes, n_nodes]
        Sigma : ndarray of rank 2
            Estimated input noise covariance. Shape [n_nodes, n_nodes]
        d_fit : dictionary
            A dictionary with diagnostics of the fit. Keys are: ['iterations',
            'distance', 'correlation'].
        """
        
        if (not type(X) == np.ndarray) or (not X.ndim==2):
            raise TypeError("""Argument X must be matrix (time x nodes).""")
        n_T, self.n_nodes = np.shape(X)

        # Make sure a correct optimization method was entered
        if method not in ['lyapunov', 'moments']:
            raise ValueError("""Please enter a valid method: 'lyapunov' or 'moments'.""")

        # A dictionary to store the diagnostics of fit
        self.d_fit = dict()

        # Number of time shifts for covariances Q_emp
        n_tau = 3
        # Lag (time-shifted) FC matrices
        Q_emp = np.zeros([n_tau, self.n_nodes, self.n_nodes], dtype=np.float)
        # Remove mean in the time series
        centered_X = X - X.mean(axis=0)
        # Calculate the lagged FC matrices
        n_T_span = n_T - n_tau + 1
        for i_tau in range(n_tau):
            Q_emp[i_tau] = np.tensordot(centered_X[0:n_T_span], \
                                        centered_X[i_tau:n_T_span+i_tau], \
                                        axes=(0,0))
        Q_emp /= float(n_T_span - 1)

        # call adequate method for optimization and check for specific arguments
        if method=='lyapunov':
            return self.fit_LO(Q_emp, **kwargs)
        elif method == 'moments':
            return self.fit_moments(Q_emp[0], Q_emp[1])

    def fit_LO(self, Q_obj, i_tau_opt=1, mask_C=None, mask_Sigma=None, norm_fc=None,
            epsilon_C=0.0005, epsilon_Sigma=0.05, min_val_C=0.0, max_val_C=1.0,
            min_val_Sigma_diag=0.0, n_opt=10000, regul_C=0.0, regul_Sigma=0.0):
        """
        Estimation of MOU parameters (connectivity C, noise covariance Sigma,
        and time constant tau_x) with Lyapunov optimization as in: Gilson et al.
        Plos Computational Biology (2016).

        Parameters
        ----------
        Q_obj : ndarray
            The covariance matrix
        i_tau_opt : integer (optional)
            Mask of known non-zero values for connectivity matrix, for example
            estimated by DTI.
        mask_C : boolean ndarray of rank-2 (optional)
            Mask of known non-zero values for connectivity matrix, for example
            estimated by DTI.
        norm_fc : float (optional)
            Normalization factor for FC. Normalization is needed to avoid high
            connectivity value that make the network activity explode. FC is
            normalized as FC *= 0.5/norm_fc. norm_fc can be specified to be for
            example the average over all entries of FC for all subjects or
            sessions in a given group. If not specified the normalization factor
            is the mean of 0-lag covariance matrix of the time series X.
        epsilon_EC : float (optional)
            Learning rate for connectivity (this should be about n_nodes times
            smaller than epsilon_Sigma).
        epsilon_Sigma : float (optional)
            Learning rate for Sigma (this should be about n_nodes times larger
            than epsilon_EC).
        min_val_EC : float (optional)
            Minimum value to bound connectivity estimate. This should be zero
            or slightly negative (too negative limit can bring to an inhibition
            dominated system). If the empirical covariance has many negative
            entries then a slightly negative limit can improve the estimation
            accuracy.
        max_val_EC : float (optional)
            Maximum value to bound connectivity estimate. This is useful to
            avoid large weight that make the system unstable. If the estimated
            connectivity saturates toward this value (it usually doesn't happen)
            it can be increased.
        n_opt : integer (optional)
            Number of maximum optimization steps. If final number of iterations
            reaches this maximum it means the algorithm has not converged.
            GORKA: variable n_opt should be renamed as maxiter.
        regul_EC : float (optional)
            Regularization parameter for connectivity. Try first a value of 0.5.
        regul_Sigma : float (optional)
            Regularization parameter for Sigma. Try first a value of 0.001.

        Returns
        -------
        J : ndarray of rank 2
            The estimated Jacobian. Shape [n_nodes, n_nodes]
        Sigma : ndarray of rank 2
            Estimated noise covariance. Shape [n_nodes, n_nodes]
        d_fit : dictionary
            A dictionary with diagnostics of the fit. Keys are: ['iterations',
            'distance', 'correlation'].
        """
        # TODO: look into regularization
        # TODO (MAT: I THINK IT IS FINE TO KEEP IT AS OPTION IN OPTIMIZATION METHOD): move SC_make to __init__() 
        # TODO: make better graphics (deal with axes separation, etc.)

        if (not type(i_tau_opt) == int) or (i_tau_opt == 0):
            raise ValueError('Scalar value i_tau_opt must be non-zero')

        # Objective FC matrices (empirical)
        Q0_obj = Q_obj[0]
        Qtau_obj = Q_obj[i_tau_opt]
#        print('Lyapunov optimization, time lag:',i_tau_opt)

        # Autocovariance time constant (exponential decay)
        log_ac = np.log( np.maximum( Q_obj.diagonal(axis1=1,axis2=2), 1e-10 ) )
        v_tau = np.arange(Q_obj.shape[0], dtype=np.float)
        lin_reg = np.polyfit( np.repeat(v_tau, self.n_nodes), log_ac.reshape(-1), 1 )
        tau_obj = -1.0 / lin_reg[0]

        # coefficients to 
        norm_Q0_obj = np.linalg.norm(Q0_obj)
        norm_Qtau_obj = np.linalg.norm(Qtau_obj)
        coef_0 = norm_Qtau_obj / (norm_Qtau_obj + norm_Q0_obj)
        coef_tau = 1.0 - coef_0

        # mask for existing connections for EC and Sigma
        mask_diag = np.eye(self.n_nodes, dtype=bool)
        if mask_C is None:
            # Allow all possible connections to be tuned except self-connections (on diagonal)
            mask_C = np.logical_not(mask_diag)
        if mask_Sigma is None:
            # Independent noise (no cross-covariances for Sigma)
            mask_Sigma = np.eye(self.n_nodes, dtype=bool)

        # Initialise network and noise. Give initial parameters
        C = np.zeros([self.n_nodes, self.n_nodes], dtype=np.float)
        tau_x = np.copy(tau_obj)
        Sigma = np.eye(self.n_nodes, dtype=np.float)

        # Best distance between model and empirical data
        best_dist = 1e10
        best_Pearson = 0.0

        # Arrays to record model parameters and outputs
        # model error = matrix distance between FC matrices
        dist_Q_hist = np.zeros([n_opt], dtype=np.float)
        # Pearson corr between model and objective FC matrices
        Pearson_Q_hist = np.zeros([n_opt], dtype=np.float)

        # run the optimization process
        stop_opt = False
        i_opt = 0
        while not stop_opt:

            # calculate Jacobian of dynamical system
            J = -np.eye(self.n_nodes, dtype=np.float) / tau_x + C

            # Calculate Q0 and Qtau for model
            Q0 = spl.solve_lyapunov(J, -Sigma)
            Qtau = np.dot( Q0, spl.expm( J.T*i_tau_opt ) )

            # difference matrices between model and objectives
            Delta_Q0 = Q0_obj - Q0
            Delta_Qtau = Qtau_obj - Qtau

            # Calculate error between model and empirical data for Q0 and FC_tau (matrix distance)
            dist_Q0 = np.linalg.norm(Delta_Q0) / norm_Q0_obj
            dist_Qtau = np.linalg.norm(Delta_Qtau) / norm_Qtau_obj
            dist_Q_hist[i_opt] = 0.5 * (dist_Q0 + dist_Qtau)

            # Calculate corr between model and empirical data for Q0 and FC_tau
            Pearson_Q0 = stt.pearsonr( Q0.reshape(-1), Q0_obj.reshape(-1) )[0]
            Pearson_Qtau = stt.pearsonr( Qtau.reshape(-1), Qtau_obj.reshape(-1) )[0]
            Pearson_Q_hist[i_opt] = 0.5 * (Pearson_Q0  + Pearson_Qtau)

            # Best fit given by best Pearson correlation coefficient
            # for both Q0 and Qtau (better than matrix distance)
            if dist_Q_hist[i_opt] < best_dist:
                    best_dist = dist_Q_hist[i_opt]
                    best_Pearson = Pearson_Q_hist[i_opt]
                    J_best = np.copy(J)
                    Sigma_best = np.copy(Sigma)
            else:
                # wait at least 5 optimization steps before stopping
                stop_opt = i_opt > 5

            # Jacobian update with weighted FC updates depending on respective error
            Delta_J = np.dot( np.linalg.pinv(Q0), coef_0 * Delta_Q0 \
                             + np.dot( coef_tau * Delta_Qtau, spl.expm(-J.T * i_tau_opt) ) ).T / i_tau_opt

            # Update effective conectivity matrix (regularization is L2)
            C[mask_C] += epsilon_C * ( Delta_J - regul_C * C )[mask_C]
            C[mask_C] = np.clip(C[mask_C], min_val_C, max_val_C)

            # Update noise matrix Sigma (regularization is L2)
            Delta_Sigma = - np.dot(J, Delta_Q0) - np.dot(Delta_Q0, J.T)
            Sigma[mask_Sigma] += epsilon_Sigma * ( Delta_Sigma - regul_Sigma * Sigma )[mask_Sigma]
            Sigma[mask_diag] = np.maximum(Sigma[mask_diag], min_val_Sigma_diag)

            # Check if max allowed number of iterations have been reached
            if i_opt >= n_opt-1:
                stop_opt = True
                print("Optimization did not converge. Maximum number of iterations arrived.")
            # Check if iteration has finished or still continues
            if stop_opt:
                self.d_fit['iterations'] = i_opt+1
                self.d_fit['distance'] = best_dist
                self.d_fit['correlation'] = best_Pearson
                self.d_fit['distance history'] = dist_Q_hist
                self.d_fit['correlation history'] = Pearson_Q_hist
            else:
                i_opt += 1

        # Save the results and return
        self.J = J_best # matrix
        self.Sigma = Sigma_best # matrix

        return self

    def fit_moments(self, Q0_obj, Q1_obj, mask_C=None):
        """
        Estimation of MOU parameters (connectivity C, noise covariance Sigma,
        and time constant tau_x) with moments method.

        Parameters
        ----------
        Q0_obj : ndarray of rank 2
            The zero-lag covariance matrix of the time series to fit.
        Q1_obj : ndarray of rank 2
            The 1-lag covariance matrix of the time series to fit.
        mask_C : boolean ndarray of rank-2 (optional)
            Mask of known non-zero values for connectivity matrix, for example
            estimated by DTI.

        Returns
        -------
        J : ndarray of rank 2
            The estimated Jacobian. Shape [n_nodes, n_nodes]
        Sigma : ndarray of rank 2
            Estimated noise covariance. Shape [n_nodes, n_nodes]
        d_fit : dictionary
            A dictionary with diagnostics of the fit. Keys are: ['iterations',
            'distance', 'correlation'].
        """
        # Jacobian estimate
        inv_Q0 = np.linalg.inv(Q0_obj)
        J = spl.logm( np.dot(inv_Q0, Q1_obj) ).T
        # Sigma estimate
        Sigma = - np.dot(J, Q0_obj) - np.dot(Q0_obj, J.conjugate())

        # masks for existing positions
        mask_diag = np.eye(self.n_nodes, dtype=np.bool)
        if mask_C is None:
            # Allow all possible connections to be tuned except self-connections (on diagonal)
            mask_C = np.logical_not(mask_diag)
            
        # cast to real matrices
        if np.any(np.iscomplex(J)):
            print("Warning: complex values in J; casting to real!")
        J_best = np.real(J)
        J_best[np.logical_not(np.logical_or(mask_C,mask_diag))] = 0
        if np.any(np.iscomplex(Sigma)):
            print("Warning: complex values in Sigma; casting to real!")
        Sigma_best = np.real(Sigma)

        # model theoretical covariances with real J and Sigma
        Q0 = spl.solve_lyapunov(J_best, -Sigma_best)
        Q1 = np.dot( Q0, spl.expm(J_best.T) )

        # Calculate error between model and empirical data for Q0 and FC_tau (matrix distance)
        dist_Q0 = np.linalg.norm(Q0 - Q0_obj) / np.linalg.norm(Q0_obj)
        dist_Qtau = np.linalg.norm(Q1 - Q1_obj) / np.linalg.norm(Q1_obj)
        self.d_fit['distance'] = 0.5 * (dist_Q0 + dist_Qtau)

        # Average correlation between empirical and theoretical
        Pearson_Q0 = stt.pearsonr( Q0.reshape(-1), Q0_obj.reshape(-1) )[0]
        Pearson_Qtau = stt.pearsonr( Q1.reshape(-1), Q1_obj.reshape(-1) )[0]
        self.d_fit['correlation'] = 0.5 * (Pearson_Q0 + Pearson_Qtau)

        # Save the results and return
        self.J = J_best # matrix
        self.Sigma = Sigma_best # matrix

        return self

    def score(self):
        """
        Returns the correlation between goodness of fit of the MOU to the 
        data, measured by the Pearson correlation between the obseved 
        covariances and the model covariances. 
        """
        try:
            return self.d_fit['correlation']
        except:
            print('The model should be fitted first.')
            return np.nan
            ## GORKA: Shall this raise a RunTimeWarning or other type of warning?

    def model_covariance(self, tau=0.0):
        """
        Calculates theoretical (lagged) covariances of the model given the
        parameters (forward step). Notice that this is not the empirical
        covariance matrix as estimated from simulated time series.

        Parameters
        ----------
        tau : scalar
            The time lag to calculate the covariance. It can be a positive or
            negative.

        Returns
        -------
        FC : ndarray of rank-2
            The (lagged) covariance matrix.
        """

        # Calculate zero lag-covariance Q0 by solving Lyapunov equation
        Q0 = spl.solve_lyapunov(self.J, -self.Sigma)
        # Calculate the effect of the lag (still valid for tau = 0.0)
        if tau>=0.0:
            return np.dot(Q0, spl.expm(tau * self.J.T))
        else:
            return np.dot(spl.expm(-tau * self.J), Q0)

    def simulate(self, T=100, dt=0.05, random_state=None):
        """
        Simulate the MOU process with simple Euler integration defined by the
        time step.

        Parameters
        ----------
        T : integer (optional)
            Duration of simulation.
        dt : scalar (optional)
            Integration time step.
        random_state : long or int (optional)
            Description here ...

        Returns
        --------
        ts : ndarray of rank-2
            Time series of simulated network activity of shape [T, n_nodes]

        Notes
        -----
        It is possible to include an acitvation function to
        give non linear effect of network input; here assumed to be identity
        """
        ## GORKA: The function should return also the time-points for the
        ## sampled resolution, for plotting of the time-series
        # 0) SECURITY CHECKS
        if dt<0.:
            raise ValueError("Integration step has to be positive. dt<0 given.")
        if T<=dt:
            raise ValueError("Duration of simulation too short. T<dt given.")
        # set seed for reproducibility
        if random_state is not None:
            np.random.seed(random_state)

        # 1) PREPARE FOR THE SIMULATION
        # 1.1) Simulation time
        # initial period to remove effect of initial conditions
        T0 = int(10. / (self.J.diagonal()).min())
        # Sampling to get 1 point every second
        n_sampl = int(1. / dt)
        # simulation time in discrete steps
        n_T = int( np.ceil(T / dt) )
        n_T0 = int(T0 / dt)

        # 1.2) Initialise the arrays
        # Array for generated time-series
        ts = np.zeros([int(n_T/n_sampl), self.n_nodes], dtype=np.float)
        # Set initial conditions for activity
        x_tmp = np.random.normal(size=[self.n_nodes])
        # Generate noise for all time steps before simulation
        noise = np.random.normal(size=[n_T0+n_T, self.n_nodes], scale=(dt**0.5))

        # 2) RUN THE SIMULATION
        # rescaled inputs and Jacobian with time step of simulation
        mu_dt = self.mu * dt
        J_dt = self.J * dt
        # calculate square root matrix of Sigma
        sqrt_Sigma = spl.sqrtm(self.Sigma)
        for t in np.arange(n_T0+n_T):
            # update of activity
            x_tmp += np.dot(J_dt, x_tmp) + mu_dt + np.dot(sqrt_Sigma, noise[t])
            # Discard first n_T0 timepoints
            if t>=n_T0:
                # Subsample timeseries (e.g. to match fMRI time resolution)
                if np.mod(t-n_T0,n_sampl)==0:
                    # save the result into the array
                    ts[int((t-n_T0)/n_sampl)] = x_tmp

        return ts
