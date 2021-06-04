# import standard packages

# import external packages
import numpy as np
from mendeleev import element
from math import pi

# import internal packages
import constants
import check_inputs
import config
import staticKS
import gridmod
import xc
import convergence
import writeoutput


class ISModel:
    def __init__(
        self,
        atom,
        xfunc_id=config.xfunc_id,
        cfunc_id=config.cfunc_id,
        bc=config.bc,
        spinpol=config.spinpol,
        spinmag=-1,
        unbound=config.unbound,
    ):
        """
        Defines the parameters used for an energy calculation.
        These are choices for the theoretical model, not numerical parameters for implementation

        Inputs (all optional):
        - xfunc    (str)   : code for libxc exchange functional     (use "None" for no exchange func)
        - cfunc    (str)   : code for libxc correlation functional  (use "None" for no correlation func)
        - bc       (int)   : choice of boundary condition (1 or 2)
        - spinpol  (bool)  : spin-polarized calculation
        - spinmag (int)    : spin-magentization
        - unbound  (str)   : treatment of unbound electrons

        Parameters
        ----------
        atom : obj
            The atom object
        xfunc : Union[str,int], optional
            The exchange functional, can be the libxc code or string, or special internal value
            Default : "lda_x"
        cfunc : Union[str,int], optional
            The correlation functional, can be the libxc code or string, or special internal value
            Default : "lda_c_pw"
        bc : str, optional
            The boundary condition, can be "dirichlet" or "neumann"
            Default : "dirichlet"
        spinpol : bool, optional
            Whether to run a spin-polarized calculation
            Default : False
        spinmag : int, optional
            The spin-magentization
            Default: 0 for nele even, 1 for nele odd
        unbound : str, optional
            The way in which the unbound electron density is computed
            Default : "ideal"

        Attributes
        ----------
        xfunc : str
            The (short-hand) name of the exchange functional
        cfunc : str
            The (short-hand) name of the correlation functional
        bc : str
            The boundary condition
        spinpol : bool
            Whether calculation will be spin-polarized
        nele : numpy array
            Number of electrons in each spin channel (total if spinpol=False)
        unbound : str
            The treatment of unbound electrons
        """

        # Input variables

        # check the spin polarization
        config.spinpol = spinpol
        self.spinpol = spinpol

        # set the spinpol param (leading dimension for density, orbitals etc)
        if config.spinpol == True:
            config.spindims = 2
        else:
            config.spindims = 1

        # spin magnetization has to be compatible with total electron number
        spinmag = check_inputs.Atom().check_spinmag(spinmag, atom.nele)

        # calculate electron number in (each) spin channel
        config.nele = check_inputs.Atom().calc_nele(spinmag, atom.nele)
        self.nele = config.nele

        # check the xc functionals
        config.xfunc, config.cfunc = check_inputs.ISModel.check_xc(xfunc_id, cfunc_id)
        self.xfunc_id = config.xfunc._xc_func_name
        self.cfunc_id = config.cfunc._xc_func_name

        # check the boundary condition
        config.bc = check_inputs.ISModel.check_bc(bc)
        self.bc = config.bc

        # check the unbound electron treatment
        config.unbound = check_inputs.ISModel.check_unbound(unbound)
        self.unbound = config.unbound

        # write output information
        output_str = writeoutput.write_ISModel_data(self)
        print(output_str)

    def CalcEnergy(self, nmax, lmax, grid_params={}, conv_params={}, scf_params={}):

        """
        Runs a self-consistent calculation to minimize the Kohn--Sham free energy functional

        Parameters
        ----------
        nmax : int
            maximum no. eigenvalues to compute for each value of angular momentum
        lmax : int
            maximum no. angular momentum eigenfunctions to consider
        grid_params : dict, optional
            dictionary of grid parameters as follows
            {'ngrid'    (int)    : number of grid points
             'x0'       (float)  : LHS grid point takes form r0=exp(x0); x0 can be specified }
        conv_params dict, optional
            dictionary of convergence parameters as follows
            {'econv'    (float)  : convergence for total energy
             'nconv'    (float)  : convergence for density
             'vconv'  (float)  : convergence for electron number}
        scf_params : dict, optional
            dictionary for scf cycle parameters as follows
            {'maxscf'   (int)    : maximum number of scf cycles
             'mixfrac'  (float)  : density mixing fraction}

        Returns
        -------
        obj
            Total energy object
        """

        # reset global parameters if they are changed
        config.nmax = nmax
        config.lmax = lmax
        config.grid_params = check_inputs.EnergyCalcs.check_grid_params(grid_params)
        config.conv_params = check_inputs.EnergyCalcs.check_conv_params(conv_params)
        # config.scf_params = scf_params.EnergyCalcs.check_scf_params(scf_params)

        # set up the grids
        gridmod.grid_setup()

        # initialize orbitals
        orbs = staticKS.Orbitals()
        # use coulomb potential as initial guess
        v_init = staticKS.Potential.calc_v_en()
        orbs.compute(v_init, init=True)

        # occupy orbitals
        orbs.occupy()

        # write the initial spiel
        scf_init = writeoutput.SCF.write_init()
        print(scf_init)

        # initialize the convergence object
        conv = convergence.SCF()

        for iscf in range(config.scf_params["maxscf"]):

            # construct density
            rho = staticKS.Density(orbs)

            # construct potential
            pot = staticKS.Potential(rho)

            # compute energies
            energy = staticKS.Energy(orbs, rho)
            E_free = energy.F_tot

            # mix potential
            if iscf > 1:
                alpha = config.scf_params["mixfrac"]
                v_s = alpha * pot.v_s + (1 - alpha) * v_s_old
            else:
                v_s = pot.v_s

            # update the orbitals with the KS potential
            orbs.compute(v_s)
            orbs.occupy()

            # update old potential
            v_s_old = v_s

            # test convergence
            conv_vals = conv.check_conv(E_free, v_s, rho.total, iscf)

            # write scf output
            scf_string = writeoutput.SCF.write_cycle(iscf, E_free, conv_vals)
            print(scf_string)

            # exit if converged
            if conv_vals["complete"]:
                break

        # write final output
        scf_final = writeoutput.SCF().write_final(energy, orbs, rho, conv_vals)
        print(scf_final)

        rho.write_to_file()

        return energy


# scf_string = self.print_scf_complete(conv_vals)
