# mezzo
Music player designed to function like major streaming platforms

## development
Build the flatpak with the following command:
```
flatpak-builder --force-clean --install-deps-from=flathub build-dir manifest.yml
```

Test the app:
```
flatpak-builder --run build-dir manifest.yml /app/mezzo
```

dependencies:
```
python3 -m pip wheel -r requirements.txt -w build-dir/files/lib/python3.8/site-packages
```

python3.11.9
