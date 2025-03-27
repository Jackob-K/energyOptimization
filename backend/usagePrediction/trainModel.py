"""
Program načte připravená data z modulu pro přípravu dat,
trénuje XGBoost regresní model s optimalizací hyperparametrů,
vyhodnocuje jeho predikce a ukládá nejlepší model a metriky na disk.

Vstup: Data připravená funkcí prepareTrainTestData()
Výstup: Uložený nejlepší model v adresáři Models a metriky výkonu modelu
Spolupracuje s: backend.database.getDb, backend.usagePrediction.prepareTrainTestData
"""

# Standardní knihovny
import os

# Externí knihovny
import joblib
import numpy as np
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score

# Lokální importy
from backend.usagePrediction.dataProcessor import prepareTrainTestData

# Načtení trénovacích/testovacích dat
xTrain, xTest, yTrain, yTest = prepareTrainTestData()

# Definice gridu pro hledání nejlepších hyperparametrů
paramGrid = {
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
    "n_estimators": [100, 200, 300],
    "max_depth": [4, 6, 8],
    "learning_rate": [0.01, 0.05, 0.1]
}

# Inicializace modelu a grid search
model = xgb.XGBRegressor(objective="reg:squarederror", random_state=42)
gridSearch = GridSearchCV(
    model,
    paramGrid,
    scoring="neg_mean_squared_error",
    cv=5,
    n_jobs=-1,
    verbose=2
)

# Trénování modelu
gridSearch.fit(xTrain, yTrain)

# Výběr nejlepšího modelu a predikce
bestModel = gridSearch.best_estimator_
yPred = bestModel.predict(xTest)

# Výpočet metrik
rmse = np.sqrt(mean_squared_error(yTest, yPred))
r2 = r2_score(yTest, yPred)

print(f"✅ Data připravena! Trénovací sada: {xTrain.shape}, Testovací sada: {xTest.shape}")
print(f"📌 RMSE: {rmse:.2f}")
print(f"📌 R2 skóre: {r2:.4f}")
print(f"📌 Nejlepší hyperparametry: {gridSearch.best_params_}")

# Uložení modelu a metrik
modelDir = "backend/usagePrediction/Models"
os.makedirs(modelDir, exist_ok=True)

modelPath = os.path.join(modelDir, "xgboostModel.pkl")
joblib.dump(bestModel, modelPath)
print(f"✅ Nejlepší model uložen jako {modelPath}")

metrics = {"RMSE": rmse, "R2": r2}
metricsPath = os.path.join(modelDir, "modelMetrics.pkl")
joblib.dump(metrics, metricsPath)
print(f"✅ Metriky modelu uloženy jako {metricsPath}")
