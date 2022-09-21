"""
Visualize interpret is for visualizations that help explain why a model makes a
certain prediction. 
"""

from olorenchemengine.base_class import *
from olorenchemengine.representations import *
from olorenchemengine.dataset import *
from olorenchemengine.uncertainty import *
from olorenchemengine.interpret import *
from olorenchemengine.internal import *
from olorenchemengine.manager import *
from olorenchemengine.visualizations import *

from tqdm import tqdm
from rdkit import Chem

class VisualizePredictionSensitivity(BaseVisualization):
    """
    Visualize the sensitivity of a model's prediction to atom-level perturbations
    generated by the SwapMutations perturbations engine.

    Parameters:
        model (BaseModel): The model to interpret.
        query_compound (str): The smiles string of the compound to interpret.
        radius (int): The radius of the perturbations to generate with SwapMutations
        n (int): The number of perturbations to generate centerred aroudn each atom.
    """

    @log_arguments
    def __init__(self, model: BaseModel, query_compound: str, radius: int = 2,
        n: int = 200, colorscale = "viridis", bottom_quantile = 0.75,
        top_quantile = 0.95, nbins = 3, log=True, **kwargs):

        super().__init__(log=False, **kwargs)
        self.packages = ["olorenrenderer"]

        self.mutator = SwapMutations(radius = radius)
        self.model = model
        self.colorscale = colorscale
        self.bottom_quantile = bottom_quantile
        self.top_quantile = top_quantile
        self.nbins = nbins

        self.smiles = query_compound
        self.mol = Chem.MolFromSmiles(self.smiles)

        vals = []
        for i, a in tqdm(enumerate(self.mol.GetAtoms())):
            smiles_list = []
            for i in range(n):
                smiles = self.mutator.get_compound_at_idx(Chem.Mol(self.mol), a.GetIdx())
                if smiles is None or Chem.MolFromSmiles(smiles) is None:
                    continue
                else:
                    smiles_list.append(smiles)
            if len(smiles_list) > 3:
                preds = self.model.predict(smiles_list)
                stdev = np.std(preds)
                a.SetDoubleProp("stdev", stdev)
                vals.append(stdev)
            else:
                print("Not enough perturbations for atom", a.GetIdx())
        
        bottom_threshold = np.quantile(vals, self.bottom_quantile)
        top_threshold = np.quantile(vals, self.top_quantile)

        for a in self.mol.GetAtoms():
            if a.HasProp("stdev"):
                val = a.GetDoubleProp("stdev")
                if val <= bottom_threshold:
                    pass
                elif val >= top_threshold:
                    a.SetDoubleProp("bin", 1)
                    a.SetAtomMapNum(self.nbins)
                else:
                    normalized_val = (val - bottom_threshold) / (top_threshold - bottom_threshold)
                    bin_number = np.around(normalized_val * self.nbins)
                    if int(bin_number) > 0:
                        a.SetAtomMapNum(int(bin_number))

    def get_data(self):
        
        import plotly

        def rgb_to_hex(x, colorscale = self.colorscale):
            if not isinstance(x, list):
                x = [x]
            x = plotly.colors.sample_colorscale(colorscale, x, colortype="hex")
            x = np.rint(np.array(x)*255).astype(int)
            return ['#%02x%02x%02x' % (x_[0], x_[1], x_[2]) for x_ in x]

        return {
            "SMILES": Chem.MolToSmiles(self.mol),
            "highlights": [
                [i+1, rgb_to_hex((i+1)/self.nbins)[0]]  for i in range(self.nbins)
            ]
        }
