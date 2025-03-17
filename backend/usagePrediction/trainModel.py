"""
Program načte připravená data z modulu pro přípravu dat,
trénuje XGBoost regresní model s optimalizací hyperparametrů,
vyhodnocuje jeho predikce a ukládá nejlepší model a metriky na disk.

Vstup: Data připravená funkcí prepareTrainTestData()
Výstup: Uložený nejlepší model v adresáři Models a metriky výkonu modelu
Spolupracuje s: backend.database.getDb, backend.usagePrediction.prepareTrainTestData

Změny názvů funkcí a proměnných:
- X_train, X_test, y_train, y_test ponechány dle návaznosti na přípravu dat
- best_model → bestModel
- model_dir → modelDir
- model_path → modelPath
"""

# Standardní knihovny
import os

# Externí knihovny
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

# Lokální importy
from backend.usagePrediction.dataProcessor import prepareTrainTestData

# prepareTrainTestData
X_train, X_test, y_train, y_test = prepareTrainTestData()

# gridSearch hyperparametrů
paramGrid = {
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
    "n_estimators": [100, 200, 300],
    "max_depth": [4, 6, 8],
    "learning_rate": [0.01, 0.05, 0.1]
}

# Inicializace a trénování modelu
from sklearn.model_selection import GridSearchCV
import xgboost as xgb

model = xgb.XGBRegressor(objective="reg:squarederror", random_state=42)
gridSearch = GridSearchCV(model, paramGrid, scoring="neg_mean_squared_error", cv=5, n_jobs=-1, verbose=2)
gridSearch.fit(X_train, y_train)

# Vyhodnocení modelu
bestModel = gridSearch.best_estimator_
y_pred = bestModel.predict(X_test)

from sklearn.metrics import mean_squared_error, r2_score

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print(f"✅ Data připravena! Trénovací sada: {X_train.shape}, Testovací sada: {X_test.shape}")
print(f"📌 RMSE: {rmse:.2f}")
print(f"📌 R2 skóre: {r2:.4f}")
print(f"📌 Nejlepší hyperparametry: {gridSearch.best_params_}")

# Uložení nejlepšího modelu
import os
import joblib

modelDir = "backend/usagePrediction/Models"
os.makedirs(modelDir, exist_ok=True)

modelPath = os.path.join(modelDir, "xgboost_model.pkl")
bestModel = gridSearch.best_estimator_
joblib.dump(bestModel, modelPath)
print(f"✅ Nejlepší model uložen jako {modelPath}")

# Uložení metrik
metrics = {"RMSE": rmse, "R2": r2}
metricsPath = os.path.join(modelDir, "model_metrics.pkl")
joblib.dump(metrics, metricsPath)
print(f"✅ Metriky modelu uloženy jako {metricsPath}")
