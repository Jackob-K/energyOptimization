import xgboost as xgb
import joblib
import os
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV
from backend.usagePrediction.dataProcessor import prepare_train_test_data

model_dir = "backend/usagePrediction/Models"
os.makedirs(model_dir, exist_ok=True)  # ✅ Vytvoří složku, pokud neexistuje

# ✅ 1. Načtení dat
X_train, X_test, y_train, y_test = prepare_train_test_data()

# ✅ 2. Definujeme model a hyperparametry pro GridSearchCV
param_grid = {
    "n_estimators": [100, 200, 300],
    "learning_rate": [0.01, 0.05, 0.1],
    "max_depth": [4, 6, 8],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0]
}

# ✅ 3. Inicializace modelu
model = xgb.XGBRegressor(objective="reg:squarederror", random_state=42)

# ✅ 4. GridSearchCV pro nalezení nejlepších hyperparametrů
print("🚀 Hledání nejlepších hyperparametrů pomocí GridSearchCV...")
grid_search = GridSearchCV(
    model, param_grid, cv=3, scoring="neg_mean_squared_error", verbose=2, n_jobs=-1
)
grid_search.fit(X_train, y_train)

# ✅ 5. Použití nejlepšího modelu pro predikci
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)

# ✅ 6. Vyhodnocení výkonu modelu
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print(f"📊 RMSE: {rmse:.4f}")
print(f"📈 R² Score: {r2:.4f}")
print(f"✅ Nejlepší hyperparametry: {grid_search.best_params_}")

# ✅ 7. Uložení nejlepšího modelu
model_path = os.path.join(model_dir, "xgboost_model.pkl")
joblib.dump(best_model, model_path)
print(f"✅ Nejlepší model uložen jako {model_path}")

# ✅ 8. Uložení metrik spolu s modelem
metrics = {
    "rmse": rmse,
    "r2_score": r2
}
metrics_path = os.path.join(model_dir, "xgboost_metrics.pkl")
joblib.dump(metrics, metrics_path)
print(f"✅ Metriky modelu uloženy jako {metrics_path}")
