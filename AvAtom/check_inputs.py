"""
This module checks inputs for errors
"""

# standard python packages
import sys

# external packages
from mendeleev import element
import sqlalchemy.orm.exc as ele_chk
import numpy as np
from math import pi

# internal packages
import unitconv
import xc
import config


# define some custom types

intc = (int, np.integer)  # unfifying type for integers


class Atom:
    """
    Checks the inputs from the BuildAtom class
    """

    def check_species(self, species):
        """
        Checks the species is a string and corresponds to an actual element

        Inputs:
        - species (str)    : chemical symbol for atomic species
        """
        if isinstance(species, str) == False:
            raise InputError.species_error("element is not a string")
        else:
            try:
                return element(species)
            except ele_chk.NoResultFound:
                raise InputError.species_error("invalid element")

    def check_units_temp(self, units_temp):
        units_accepted = ["ha", "ev", "k"]
        if units_temp.lower() not in units_accepted:
            raise InputError.temp_error("units of temperature are not recognised")
        return units_temp.lower()

    def check_temp(self, temp, units_temp):
        """
        Checks the temperature is a float within a sensible range
        """

        if not isinstance(temp, (float, intc)):
            raise InputError.temp_error("temperature is not a number")
        else:
            # convert internal temperature to hartree
            if units_temp.lower() == "ev":
                temp = unitconv.ev_to_ha * temp
            elif units_temp.lower() == "k":
                temp = unitconv.K_to_ha * temp
            # check if temperature is within some reasonable limits
            if temp < 0:
                raise InputError.temp_error("temperature is negative")
            if temp < 0.01:
                print(InputWarning.temp_warning("low"))
                return temp
            elif temp > 3.5:
                print(InputWarning.temp_warning("high"))
                return temp
            else:
                return temp

    def check_charge(self, charge):
        """
        Checks the charge is an integer
        """
        if isinstance(charge, intc) == False:
            raise InputError.charge_error()
        else:
            return charge

    def check_units_radius(self, units_radius):
        radius_units_accepted = ["bohr", "angstrom", "ang"]
        if units_radius.lower() not in radius_units_accepted:
            raise InputError.density_error("Radius units not recognised")

        return units_radius.lower()

    def check_units_density(self, units_density):
        density_units_accepted = ["g/cm3", "gcm3"]

        if units_density.lower() not in density_units_accepted:
            raise InputError.density_error("Density units not recognised")

        return units_density.lower()

    def check_radius(self, radius, units_radius):

        if not isinstance(radius, (float, intc)):
            raise InputError.density_error("Radius is not a number")

        else:
            if units_radius == "angstrom" or units_radius == "ang":
                radius = unitconv.angstrom_to_bohr * radius
            if radius < 0.1:
                raise InputError.density_error(
                    "Radius must be a positive number greater than 0.1"
                )
        return radius

    def check_density(self, density, units_density):
        if not isinstance(density, (float, intc)):
            raise InputError.density_error("Density is not a number")
        else:
            if density > 100 or density < 0:
                raise InputError.density_error(
                    "Density must be a positive number less than 100"
                )

        return density

    def check_rad_dens_init(self, atom, radius, density, units_radius, units_density):
        """
        Checks that the density or radius is specified

        Inputs:
        - atom (object)     : atom object
        - density (float)   : material density
        - radius (float)    : voronoi sphere radius
        """

        if isinstance(density, (float, intc)) == False:
            raise InputError.density_error("Density is not a number")
        if not isinstance(radius, (float, intc)):
            raise InputError.density_error("Radius is not a number")
        else:
            if units_radius == "angstrom" or units_radius == "ang":
                radius = unitconv.angstrom_to_bohr * radius
            if density == -1 and radius != -1:
                if radius < 0.1:
                    raise InputError.density_error(
                        "Radius must be a positive number greater than 0.1"
                    )
                else:
                    density = self.radius_to_dens(atom, radius)
            elif radius == -1 and density != -1:
                if density > 100 or density < 0:
                    raise InputError.density_error(
                        "Density must be a positive number less than 100"
                    )
                else:
                    radius = self.dens_to_radius(atom, density)
            elif radius != -1 and density != -1:
                density_test = self.radius_to_dens(atom, radius)
                if abs((density_test - density) / density) > 5e-2:
                    raise InputError.density_error(
                        "Both radius and density are specified but they are not compatible"
                    )
                else:
                    density = density_test
            elif radius == -1 and density == -1:
                raise InputError.density_error(
                    "One of radius or density must be specified"
                )

        return radius, density

    def radius_to_dens(self, atom, radius):
        """
        Convert the Voronoi sphere radius to a mass density
        """

        # radius in cm
        rad_cm = radius / unitconv.cm_to_bohr
        # volume in cm
        vol_cm = (4.0 * pi * rad_cm ** 3) / 3.0
        # atomic mass in g
        mass_g = config.mp_g * atom.at_mass
        # density in g cm^-3
        density = mass_g / vol_cm

        return density

    def dens_to_radius(self, atom, density):
        """
        Convert the material density to Voronoi sphere radius
        """

        # compute atomic mass in g
        mass_g = config.mp_g * atom.at_mass
        # compute volume and radius in cm^3/cm
        vol_cm = mass_g / density
        rad_cm = (3.0 * vol_cm / (4.0 * pi)) ** (1.0 / 3.0)
        # convert to a.u.
        radius = rad_cm * unitconv.cm_to_bohr

        return radius


class ISModel:
    """
    Checks the inputs for the IS model class
    """

    def check_xc(xc_func, xc_type):
        """
        checks the exchange and correlation functionals are defined by libxc
        """

        # supported families of libxc functional by name
        names_supp = ["lda"]
        # supported families of libxc functional by id
        id_supp = [1]

        # check both the exchange and correlation functionals are valid
        xc_func, err_xc = xc.check_xc_func(xc_func, id_supp)

        if err_xc == 1:
            raise InputError.xc_error(
                xctype + " functional is not an id (int) or name (str)"
            )
        elif err_xc == 2:
            raise InputError.xc_error(
                xc_type
                + " functional is not a valid name or id.\n \
                Please choose from the valid inputs listed here: \n\
                https://www.tddft.org/programs/libxc/functionals/"
            )
        elif err_xc == 3:
            raise InputError.xc_error(
                "This family of "
                + xc_type
                + " functionals is not yet supported by AvAtom. \n\
                Supported families so far are: "
                + " ".join(names_supp)
            )

        return xc_func

    def check_unbound(unbound):
        """
        Checks the input for the unbound electrons

        Parameters
        ----------
        unbound : str
            defines the treatment of the unbound electrons

        Raises
        ------
            InputError

        Returns
        -------
        str:
            description of unbound electron treatment
        """

        # list all possible treatments for unbound electrons
        unbound_permitted = ["ideal"]

        # convert unbound to all lowercase
        unbound.lower()

        if not isinstance(unbound, str):
            raise InputError.unbound_error(
                "Unbound electron description is not a string"
            )
        else:
            if unbound not in unbound_permitted:
                err_msg = (
                    "Treatment of unbound electrons not recognised. \n \
                Allowed treatments are: "
                    + [ub for ub in unbound_permitted]
                )
                raise InputError.unbound_error(err_msg)

        return unbound

    def check_bc(bc):
        """
        Checks the boundary condition is permitted

        Parameters
        ----------
        bc : str
            defines the boundary condition used to solve KS eqns

        Raises
        ------
        InputError

        Returns
        -------
        str:
            boundary condition used to solve KS eqns
        """

        # list permitted boundary conditions
        bcs_permitted = ["dirichlet", "neumann"]

        # convert to lowercase
        bc.lower()

        if not isinstance("bc", str):
            raise InputError.bc_error("Boundary condition is not a string")
        else:
            if bc not in bcs_permitted:
                err_msg = (
                    "Boundary condition is not recognised. \n \
                Allowed boundary conditions are: "
                    + [b for b in bcs_permitted]
                )
                raise InputError.bc_error(err_msg)

        return bc

    def check_spinpol(spinpol):
        """
        Parameters
        ----------
        spinpol : bool
           spin polarized calculation

        Returns
        -------
        spinpol : bool
            same as input unless error raised

        Raises
        ------
        InputError
        """

        if not isinstance(spinpol, bool):
            raise InputError.spinpol_error("Spin polarization is not of type bool")

        return spinpol

    def check_spinmag(spinmag, nele):
        """
        Checks the spin magnetization is compatible with the total electron number
        """
        if isinstance(spinmag, intc) == False:
            raise InputError.spinmag_error(
                "Spin magnetization is not a positive integer"
            )

        # computes the default value of spin magnetization
        if spinmag == -1:
            if nele % 2 == 0:
                spinmag = 0
            else:
                spinmag = 1
        elif spinmag > -1:
            if nele % 2 == 0 and spinmag % 2 != 0:
                raise InputError.spinmag_error(
                    "Spin magnetization is not compatible with total electron number"
                )
            elif nele % 2 != 0 and spinmag % 2 == 0:
                raise InputError.spinmag_error(
                    "Spin magnetization is not compatible with total electron number"
                )
        else:
            raise InputError.spinmag_error(
                "Spin magnetization is not a positive integer"
            )

        return spinmag

    def calc_nele(spinmag, nele, spinpol):
        """
        Calculates the electron number in each spin channel from spinmag
        and total electron number
        """

        if not spinpol:
            nele = np.array([nele], dtype=int)
        else:
            nele_up = (nele + spinmag) / 2
            nele_dw = (nele - spinmag) / 2
            nele = np.array([nele_up, nele_dw], dtype=int)

        return nele


class EnergyCalcs:
    @staticmethod
    def check_grid_params(grid_params):
        """
        Checks grid parameters are reasonable, or assigns if empty

        Parameters
        ----------
        grid_params : dict
            Can contain the keys "ngrid" (int, number of grid points)
            and "x0" (float, LHS grid point for log grid)

        Returns
        -------
        dict
          {'ngrid'    (int)    : number of grid points
           'x0'       (float)  : LHS grid point takes form r0=exp(x0); x0 can be specified }
        """

        # First assign the keys ngrid and x0 if they are not given
        try:
            ngrid = grid_params["ngrid"]
        except KeyError:
            ngrid = config.grid_params["ngrid"]

        try:
            x0 = grid_params["x0"]
        except KeyError:
            x0 = config.grid_params["x0"]

        # check that ngrid is an integer
        if not isinstance(ngrid, intc):
            raise InputError.grid_error("Number of grid points not an integer!")
        # check that ngrid is a positive number
        if ngrid < 0:
            raise InputError.grid_error("Number of grid points must be positive")
        elif ngrid < 500:
            print(InputWarning.ngrid_warning("low", "inaccurate"))
        elif ngrid > 5000:
            print(InputWarning.ngrid_warning("high", "expensive"))

        # check that x0 is reasonable
        if x0 > -3:
            raise InputError.grid_error(
                "x0 is too high, calculation will likely not converge"
            )

        grid_params = {"ngrid": ngrid, "x0": x0}

        return grid_params

    @staticmethod
    def check_conv_params(input_params):
        """
        Checks convergence parameters are reasonable, or assigns if empty

        Parameters
        ----------
        input_params : dict of floats
            Can contain the keys "econv", "nconv" and "vconv", for energy,
            density and potential convergence parameters

        Returns
        -------
        dict
          {'econv'    (float)    : energy convergence
           'nconv'    (float)    : density convergence
           'vconv'    (float)    : potential convergence}
        """

        conv_params = {}
        # loop through the convergence parameters
        for conv in ["econv", "nconv", "vconv"]:
            # assign value if not given
            try:
                x_conv = input_params[conv]
            except KeyError:
                x_conv = config.conv_params[conv]

            # check float
            if not isinstance(x_conv, float):
                raise InputError.conv_error(conv + " is not a float!")
            # check > 0
            elif x_conv < 0:
                raise InputError.conv_error(conv + " cannot be negative")

            conv_params[conv] = x_conv

        return conv_params

    @staticmethod
    def check_scf_params(input_params):
        """
        Checks convergence parameters are reasonable, or assigns if empty

        Parameters
        ----------
        input_params : dict
            Can contain the keys "maxscf" and "mixfrac" for max scf cycle
            and potential mixing fraction

        Returns
        -------
        scf_params : dict
            A dictionary with the following scf parameters
            {'maxscf'   (int)    : max number scf cycles
             'mixfrac'  (int)    : mixing fraction}
        """

        scf_params = {}

        # assign value to scf param if it is not specified
        for p in ["maxscf", "mixfrac"]:
            try:
                scf_params[p] = input_params[p]
            except KeyError:
                scf_params[p] = config.scf_params[p]

        # check maxscf is an integer
        maxscf = scf_params["maxscf"]
        if not isinstance(maxscf, intc):
            raise InputError.SCF_error("maxscf is not an integer!")
        # check it is at least 1
        elif maxscf < 1:
            raise InputError.SCF_error("maxscf must be at least 1")

        # check mixfrac is a float
        mixfrac = scf_params["mixfrac"]
        if not isinstance(mixfrac, float):
            raise InputError.SCF_error("mixfrac is not a float!")
        # check it lies between 0,1
        elif mixfrac < 0 or mixfrac > 1:
            raise InputError.SCF_error("mixfrac must be in range [0,1]")

        return scf_params


class InputError(Exception):
    """
    Handles errors in inputs
    """

    def species_error(err_msg):
        """
        Raises an exception if there is an invalid species

        Inputs:
        - err_msg (str)     : error message printed
        """

        print("Error in atomic species input: " + err_msg)
        print("Species must be a chemical symbol, e.g. 'He'")
        sys.exit("Exiting AvAtom")

    def temp_error(err_msg):
        """
        Raises an exception if temperature is not a float

        Inputs:
        - err_msg (str)     : error message printed
        """
        print("Error in temperature input: " + err_msg)
        print("Temperature should be >0 and given in units of eV")
        sys.exit("Exiting AvAtom")

    def charge_error():
        """
        Raises an exception if charge is not an integer
        """
        print("Error in charge input: charge is not an integer")
        sys.exit("Exiting AvAtom")

    def density_error(err_msg):
        """
        Raises an exception if density is not a float or negative

        Inputs:
        - err_msg (str)     : error message printed
        """
        print("Error in density input: " + err_msg)
        sys.exit("Exiting AvAtom")

    def spinmag_error(err_msg):
        """
        Raises an exception if density is not a float or negative
        """

        print("Error in spinmag input: " + err_msg)
        sys.exit("Exiting AvAtom")

    def xc_error(err_msg):

        """
        Raises an exception if density is not a float or negative
        """

        print("Error in xc input: " + err_msg)
        sys.exit("Exiting AvAtom")

    def unbound_error(err_msg):
        """
        Raises exception if unbound not str or in permitted values

        Parameters
        ----------
        err_msg : str
            the error message printed

        Raises
        -------
            InputError
        """

        print("Error in unbound electron input: " + err_msg)
        sys.exit("Exiting AvAtom")

    def bc_error(err_msg):
        """
        Raises exception if unbound not str or in permitted values

        Parameters
        ----------
        err_msg : str
            the error message printed

        Raises
        -------
            InputError
        """

        print("Error in boundary condition input: " + err_msg)
        sys.exit("Exiting AvAtom")

    def spinpol_error(err_msg):
        """
        Raises exception if spinpol not a boolean

        Parameters
        ----------
        err_msg : str
            the error message printed

        Raises
        -------
            InputError
        """

        print("Error in spin polarization input: " + err_msg)
        sys.exit("Exiting AvAtom")

    def grid_error(err_msg):
        """
        Raises exception if error in grid inputs

        Parameters
        ----------
        err_msg : str
            the error message printed

        Raises
        -------
            InputError
        """

        print("Error in grid inputs: " + err_msg)
        sys.exit("Exiting AvAtom")

    def conv_error(err_msg):
        """
        Raises exception if error in convergence inputs

        Parameters
        ----------
        err_msg : str
            the error message printed

        Raises
        -------
            InputError
        """

        print("Error in convergence inputs: " + err_msg)
        sys.exit("Exiting AvAtom")

    def SCF_error(err_msg):
        """
        Raises exception if error in convergence inputs

        Parameters
        ----------
        err_msg : str
            the error message printed

        Raises
        -------
            InputError
        """

        print("Error in scf_params input: " + err_msg)
        sys.exit("Exiting AvAtom")


class InputWarning:
    """
    Warns user if inputs are considered outside of typical ranges, but proceeds anyway
    """

    def temp_warning(err):
        """
        Warning if temperature outside of sensible range

        Inputs:
        - temp (float)    : temperature in units of eV
        - err (str)       : "high" or "low"
        """
        warning = (
            "Warning: this input temperature is very "
            + err
            + ". Proceeding anyway, but results may not be accurate. \n"
            + "Normal temperature range for AvAtom is 0.01 -- 100 eV \n"
        )
        return warning

    def ngrid_warning(err1, err2):
        """
        Warning if grid params outside of sensible range
        """
        warning = (
            "Warning: number of grid points is very "
            + err1
            + ". Proceeding anyway, but results may be "
            + err2
            + "\n"
            + "Suggested grid range is between 1000-5000 but should be tested wrt convergence \n"
        )
        return warning
