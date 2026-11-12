import joblib
import pandas as pd
import numpy as np

bundle = joblib.load('models/disease_prediction/logisticregression_best.joblib')
pipe = bundle['pipeline']
classes = list(bundle['classes'])
feature_names = bundle['feature_names']

val_df = pd.read_csv('data/disease_prediction/processed/val.csv')
symptom_cols = [c for c in val_df.columns if c != 'prognosis']
X_val = val_df[symptom_cols].to_numpy()
y_val = val_df['prognosis'].to_numpy()
proba_val = pipe.predict_proba(X_val)

top1 = np.max(proba_val, axis=1)
sorted_probas = np.sort(proba_val, axis=1)
top2 = sorted_probas[:, -2]
margins = top1 - top2
pred_labels = [classes[i] for i in np.argmax(proba_val, axis=1)]

print(f"Validation Total Samples: {len(y_val)}")
for min_score in [0.15, 0.20, 0.25, 0.30]:
    for min_margin in [0.03, 0.05, 0.08, 0.10]:
        confident = (top1 >= min_score) & (margins >= min_margin)
        coverage = np.mean(confident)
        acc = np.mean(y_val[confident] == np.array(pred_labels)[confident]) if np.sum(confident) > 0 else 0.0
        print(f"Score >= {min_score:.2f}, Margin >= {min_margin:.2f} -> Coverage: {coverage*100:5.1f}% ({np.sum(confident)}/{len(y_val)}), Precision: {acc*100:5.1f}%")

