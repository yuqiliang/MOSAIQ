"""
Validate MOSAIQ data using the Frictionless Python API.
Run with: python3 validate_in_python.py
"""
from frictionless import Package, Resource, validate

# --- Method 1: validate the whole package -------------------------------
print("=" * 60)
print("Validating the entire data package")
print("=" * 60)

report = validate("datapackage.yaml")

if report.valid:
    print("✅ Package is VALID")
else:
    print(f"❌ Package has {len(report.errors)} errors")
    for err in report.errors[:5]:
        print(f"   - {err.message}")

# --- Method 2: load and inspect a single resource ----------------------
print()
print("=" * 60)
print("Inspecting the clips resource")
print("=" * 60)

package = Package("datapackage.yaml")
clips = package.get_resource("clips")

print(f"Title:        {clips.title}")
print(f"Format:       {clips.format}")
print(f"Path:         {clips.path}")
print(f"Schema fields: {len(clips.schema.fields)}")

# Show the first 5 field names and their constraints
print("\nFirst 5 fields with constraints:")
for f in clips.schema.fields[:5]:
    print(f"  {f.name:25s}  type={f.type:8s}  constraints={f.constraints}")

# --- Method 3: read data row by row ------------------------------------
print()
print("=" * 60)
print("Reading first 3 rows from clips")
print("=" * 60)

with clips:
    for i, row in enumerate(clips.row_stream):
        if i >= 3:
            break
        print(f"Row {i+1}: clip_id={row['clip_id']}, "
              f"ISOPleasant={row['mean_ISOPleasant']}, "
              f"LAeq={row['LAeq_dBA']} dBA")
