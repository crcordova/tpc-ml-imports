import numpy as np

def build_histogram(data: list[tuple[float, float]], bin_width: float = 0.5):
    if not data:
        return {"bins": [], "values": []}

    precios, cantidades = zip(*data)
    min_price = min(precios)
    max_price = max(precios)
    
    bins = np.arange(min_price, max_price + bin_width, bin_width)
    
    # np.histogram acepta pesos
    hist, bin_edges = np.histogram(precios, bins=bins, weights=cantidades)
    
    # Retornar para graficar (centro del bin)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    return {"bins": bin_centers.tolist(), "values": hist.tolist()}

def build_boxplot_data(data: list[dict], max_rep: int = 100):
    output = []
    for row in data:
        rut = row["rut"]
        price = row["fob_unit"]
        cantidad = row["cantidad"] or 1
        
        # Escalamos repeticiones a un máximo razonable
        repeticiones = min(int(cantidad / max(1, cantidad // max_rep)), max_rep)
        
        # Generamos observaciones simuladas ponderadas
        for _ in range(repeticiones):
            output.append({"group": rut, "value": price})
    return output