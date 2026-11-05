# Espacio de ejemplo para la medalla audiovisual

Copia aquí el archivo que quieras que el agente revise (por ejemplo el reel o un
máster) y luego:

```bash
python -m chasis.cli trabajar \
  --medalla produccion-audiovisual --piezas archivos medios \
  --carpeta ./ejemplos/video \
  --encargo "Revisa el video antes de publicarlo: mide el archivo, el audio y busca planos negros"
```

Los videos no se versionan (pesan cientos de MB). El .gitignore los excluye.
