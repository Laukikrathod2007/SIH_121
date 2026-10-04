"""Module 5's tests import the code under test through its canonical packages
(`app.modules.predictive_analytics...`, and Module 4's `app.modules.physics...`
for the simulation -> features -> fusion -> alert chain exercised by
test_system_review.py), so no sys.path set-up is needed here: run the suite
from Backend/ (`cd Backend && pytest`), whose pytest.ini provides the import
root and import mode."""
