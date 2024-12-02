# -*- coding: utf-8 -*-
"""Cuaderno2_Parte1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/12nowkxoUxFHzTMUkrjbyU1q9pxdhRrH3
"""

#Esta es una obra derivada del original escrito por Isabelle Tingzon
# Bibliotecas estándar
import os
import random
from tqdm.notebook import tqdm
import torch

# Manipulación y visualización de datos
import matplotlib.pyplot as plt
from PIL import Image
import seaborn as sns
import pandas as pd
import numpy as np

# Bibliotecas de aprendizaje profundo
import torch
import torchvision
import torchsummary
from torch.utils import data
from torchvision import datasets, models, transforms

# Fijar semilla para reproducibilidad
SEMILLA = 42
np.random.seed(SEMILLA)

# Verificar si la GPU está habilitada
dispositivo = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("Dispositivo: {}".format(dispositivo))

# Obtener modelo específico de GPU
if str(dispositivo) == "cuda:0":
    print("GPU: {}".format(torch.cuda.get_device_name(0)))

# Montar Drive
from google.colab import drive
drive.mount('/content/drive', force_remount=True)

# Descargar y preparar datos
!wget http://madm.dfki.de/files/sentinel/EuroSAT.zip -O EuroSAT.zip
!unzip -q EuroSAT.zip -d 'EuroSAT/'
!rm EuroSAT.zip

# Transformaciones de datos
tam_entrada = 224
media_imagenet, std_imagenet = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

transformacion_entrenamiento = transforms.Compose([
    transforms.RandomResizedCrop(tam_entrada),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(media_imagenet, std_imagenet)
])

transformacion_validacion = transforms.Compose([
    transforms.Resize(tam_entrada),
    transforms.CenterCrop(tam_entrada),
    transforms.ToTensor(),
    transforms.Normalize(media_imagenet, std_imagenet)
])

transformacion_prueba = transforms.Compose([
    transforms.Resize(tam_entrada),
    transforms.CenterCrop(tam_entrada),
    transforms.ToTensor(),
    transforms.Normalize(media_imagenet, std_imagenet)
])

# Cargar el dataset
ruta_datos = './EuroSAT/2750/'
conjunto_entrenamiento = datasets.ImageFolder(
    ruta_datos, transform=transformacion_entrenamiento)
conjunto_validacion = datasets.ImageFolder(
    ruta_datos, transform=transformacion_validacion)
conjunto_prueba = datasets.ImageFolder(
    ruta_datos, transform=transformacion_prueba)

# Obtener las categorías
nombres_clases = conjunto_entrenamiento.classes
print("Nombres de clases: {}".format(nombres_clases))
print("Número total de clases: {}".format(len(nombres_clases)))

# Dividir aleatoriamente los datos
tam_entrenamiento = 0.70
tam_validacion = 0.15
tam_prueba = 1 - tam_entrenamiento - tam_validacion

indices = list(range(len(conjunto_entrenamiento)))
np.random.shuffle(indices)

tam_split_entrenamiento = int(tam_entrenamiento * len(indices))
tam_split_validacion = int(tam_validacion * len(indices))

indices_entrenamiento = indices[:tam_split_entrenamiento]
indices_validacion = indices[tam_split_entrenamiento:tam_split_entrenamiento + tam_split_validacion]
indices_prueba = indices[tam_split_entrenamiento + tam_split_validacion:]

datos_entrenamiento = data.Subset(conjunto_entrenamiento, indices_entrenamiento)
datos_validacion = data.Subset(conjunto_validacion, indices_validacion)
datos_prueba = data.Subset(conjunto_prueba, indices_prueba)

print("Tamaños de entrenamiento/validación/prueba: {}/{}/{}".format(
    len(datos_entrenamiento), len(datos_validacion), len(datos_prueba)
))

# Crear DataLoaders
tam_lote = 16
trabajadores = 2

carga_entrenamiento = data.DataLoader(
    datos_entrenamiento, batch_size=tam_lote, num_workers=trabajadores, shuffle=True
)
carga_validacion = data.DataLoader(
    datos_validacion, batch_size=tam_lote, num_workers=trabajadores, shuffle=False
)
carga_prueba = data.DataLoader(
    datos_prueba, batch_size=tam_lote, num_workers=trabajadores, shuffle=False
)

# Visualizar datos
n = 4  # Cambia n para ajustar la cuadrícula a 4x4
lote = next(iter(carga_entrenamiento))
entradas, clases = lote
figura, ejes = plt.subplots(n, n, figsize=(12, 12))  # Cambia el tamaño para una cuadrícula más grande

for i in range(n):
    for j in range(n):
        indice = i * n + j  # Índice para acceder a las imágenes en el lote
        if indice < len(entradas):
            imagen = entradas[indice].numpy().transpose((1, 2, 0))
            imagen = np.clip(np.array(std_imagenet) * imagen + np.array(media_imagenet), 0, 1)
            ejes[i, j].imshow(imagen)
            ejes[i, j].set_title(nombres_clases[clases[indice]])
            ejes[i, j].axis('off')
plt.tight_layout()
plt.show()

# Análisis exploratorio de datos
plt.figure(figsize=(6, 3))
histograma = sns.histplot([clase for _, clase in conjunto_entrenamiento])

histograma.set_xticks(range(len(nombres_clases)))
histograma.set_xticklabels(nombres_clases, rotation=90)
histograma.set_title('Histograma de clases del conjunto EuroSAT')
plt.show()

# Configuración del modelo
modelo = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
modelo.fc = torch.nn.Linear(modelo.fc.in_features, len(nombres_clases))
modelo = modelo.to(dispositivo)

torchsummary.summary(modelo, (3, tam_entrada, tam_entrada))

# Especificar número de épocas y tasa de aprendizaje
numero_epocas = 10
tasa_aprendizaje = 1e-3

# Especificar criterio y optimizador
criterio = torch.nn.CrossEntropyLoss()
optimizador = torch.optim.SGD(modelo.parameters(), lr=tasa_aprendizaje)

# Definir función de entrenamiento
def entrenar(modelo, cargador_datos, criterio, optimizador):
    modelo.train()

    perdida_acumulada = 0.0
    total_correctos = 0.0

    for i, (entradas, etiquetas) in enumerate(tqdm(cargador_datos)):
        entradas = entradas.to(dispositivo)
        etiquetas = etiquetas.to(dispositivo)

        # Reiniciar gradientes
        optimizador.zero_grad()

        # Paso hacia adelante
        salidas = modelo(entradas)

        # Calcular pérdida
        perdida = criterio(salidas, etiquetas)

        # Propagar gradientes
        perdida.backward()

        # Actualizar pesos
        optimizador.step()

        # Calcular estadísticas
        _, predicciones = torch.max(salidas, 1)
        perdida_acumulada += perdida.item() * entradas.size(0)
        total_correctos += torch.sum(predicciones == etiquetas)

    # Calcular pérdida y precisión por época
    perdida_epoca = perdida_acumulada / len(cargador_datos.dataset)
    precision_epoca = (total_correctos / len(cargador_datos.dataset)) * 100
    print(f"Perdida de entrenamiento: {perdida_epoca:.2f}; Precisión: {precision_epoca:.2f}%")

    return perdida_epoca, precision_epoca

# Definir función de evaluación
def evaluar(modelo, cargador_datos, criterio, fase="validacion"):
    modelo.eval()

    perdida_acumulada = 0.0
    total_correctos = 0.0

    for i, (entradas, etiquetas) in enumerate(tqdm(cargador_datos)):
        entradas = entradas.to(dispositivo)
        etiquetas = etiquetas.to(dispositivo)

        with torch.set_grad_enabled(False):
            salidas = modelo(entradas)
            perdida = criterio(salidas, etiquetas)
            _, predicciones = torch.max(salidas, 1)

        perdida_acumulada += perdida.item() * entradas.size(0)
        total_correctos += torch.sum(predicciones == etiquetas)

    # Calcular pérdida y precisión por época
    perdida_epoca = perdida_acumulada / len(cargador_datos.dataset)
    precision_epoca = (total_correctos / len(cargador_datos.dataset)) * 100
    print(f"{fase.title()} Perdida: {perdida_epoca:.2f}; Precisión: {precision_epoca:.2f}%")

    return perdida_epoca, precision_epoca

# Definir función de ajuste (entrenamiento y evaluación)
def ajustar(modelo, cargador_entrenamiento, cargador_validacion, numero_epocas, criterio, optimizador):
    mejor_perdida = float('inf')
    mejor_modelo = None

    for epoca in range(numero_epocas):
        print(f"Época {epoca + 1}")

        # Entrenar
        entrenar(modelo, cargador_entrenamiento, criterio, optimizador)

        # Evaluar
        perdida_validacion, _ = evaluar(modelo, cargador_validacion, criterio, fase="validacion")

        if perdida_validacion < mejor_perdida:
            mejor_perdida = perdida_validacion
            mejor_modelo = modelo

    return mejor_modelo

# Comenzar entrenamiento y evaluación
mejor_modelo = ajustar(modelo, carga_entrenamiento, carga_validacion, numero_epocas, criterio, optimizador)

# Evaluar el modelo en el conjunto de prueba
perdida_prueba, _ = evaluar(mejor_modelo, carga_prueba, criterio, fase="prueba")

# Guardar modelo
directorio_modelo = "./drive/My Drive/Colab Notebooks/modelos/"
if not os.path.exists(directorio_modelo):
    os.makedirs(directorio_modelo)

archivo_modelo = os.path.join(directorio_modelo, 'mejor_modelo.pth')
torch.save(mejor_modelo.state_dict(), archivo_modelo)
print(f"Modelo guardado exitosamente en {archivo_modelo}")

# Cargar modelo guardado
def cargar_modelo(archivo_modelo):
    modelo = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    modelo.fc = torch.nn.Linear(modelo.fc.in_features, len(nombres_clases))
    modelo.load_state_dict(torch.load(archivo_modelo))
    modelo.eval()
    print(f"Modelo cargado desde {archivo_modelo}")
    return modelo

modelo_cargado = cargar_modelo(archivo_modelo)

# Visualizar resultados en una muestra
indice = 15
imagen, etiqueta = datos_prueba[indice]

# Predicción
modelo_cargado.to("cpu")
salida = modelo_cargado(imagen.unsqueeze(0))
_, prediccion = torch.max(salida, 1)

# Mostrar resultado
etiqueta_real = nombres_clases[etiqueta]
etiqueta_prediccion = nombres_clases[prediccion[0]]

imagen = imagen.numpy().transpose((1, 2, 0))
imagen = np.clip(np.array(std_imagenet) * imagen + np.array(media_imagenet), 0, 1)

figura, eje = plt.subplots(figsize=(3, 3))
eje.imshow(imagen)
eje.set_title(f"Predicción: {etiqueta_prediccion}\nClase real: {etiqueta_real}")
plt.show()

# Ejecutar el modelo en una imagen PIL
from PIL import Image

ruta_imagen = './EuroSAT/2750/Forest/Forest_2.jpg'
imagen = Image.open(ruta_imagen)

# Transformar imagen
entrada = transformacion_prueba(imagen)

# Predicción
salida = modelo_cargado(entrada.unsqueeze(0))
_, prediccion = torch.max(salida, 1)

# Obtener etiqueta
etiqueta_prediccion = nombres_clases[prediccion[0]]

# Visualizar resultado
figura, eje = plt.subplots(figsize=(3, 3))
eje.imshow(imagen)
eje.set_title(f"Clase predicha: {etiqueta_prediccion}")
plt.show()

import os

# Listar los archivos en la carpeta para verificar
carpeta_base = '/content/drive/My Drive/Data/'
print(os.listdir(carpeta_base))

import os

# Ruta del directorio que contiene las bandas en formato .jpg
ruta_directorio = '/content/drive/My Drive/Data/S2A_MSIL2A_20240914T152651_N0511_R025_T18NVK_20240914T222508.SAFE'

# Listar los archivos con extensión .jpg
archivos = [archivo for archivo in os.listdir(ruta_directorio) if archivo.endswith('.jpg')]
print("Archivos disponibles:", archivos)

from PIL import Image
import numpy as np

# Función para cargar y combinar las bandas en una sola imagen
def cargar_imagen_satelital(ruta_directorio, archivos):
    capas = []
    for archivo in archivos:
        ruta_banda = os.path.join(ruta_directorio, archivo)
        # Cargar la banda como imagen en escala de grises
        imagen = Image.open(ruta_banda).convert('L')  # Convertir a escala de grises
        capas.append(np.array(imagen))
    # Combinar las bandas en un array multicanal (depth = número de bandas)
    imagen_multicanal = np.stack(capas, axis=-1)
    return imagen_multicanal

# Selecciona los archivos relevantes para las bandas
bandas_seleccionadas = ['S2A_MSIL2A_20240914T152651_N0511_R025_T18NVK_20240914T222508-ql.jpg']  # Ejemplo: Bandas RGB
imagen_satelital = cargar_imagen_satelital(ruta_directorio, bandas_seleccionadas)
print("Dimensiones de la imagen combinada:", imagen_satelital.shape)

from torchvision import transforms
import torch

# Normalización según ImageNet (ajusta si las bandas son diferentes)
normalizar = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

# Transformar la imagen
def preprocesar_imagen(imagen):
    # Escalar valores a [0, 1]
    imagen = imagen.astype(np.float32) / 255.0

    # Verificar y reordenar para asegurar el formato [C, H, W]
    if len(imagen.shape) == 3:  # Si tiene canales
        imagen = np.transpose(imagen, (2, 0, 1))  # Reordenar ejes [H, W, C] -> [C, H, W]
    else:  # Si es monocanal, añade un canal
        imagen = np.expand_dims(imagen, axis=0)  # [H, W] -> [1, H, W]

    # Convertir a tensor
    imagen = torch.tensor(imagen)

    # Aplicar normalización si tiene 3 canales
    if imagen.shape[0] == 3:  # Normalizar solo si hay 3 canales (RGB)
        imagen = normalizar(imagen)

    return imagen.unsqueeze(0)  # Añadir dimensión del batch

imagen_preprocesada = preprocesar_imagen(imagen_satelital)
print("Forma del tensor preprocesado:", imagen_preprocesada.shape)

import os

# Ruta base de la carpeta 'Data'
carpeta_base = '/content/drive/My Drive/Data/'

# Ruta del subdirectorio donde se encuentra el archivo
subcarpeta = os.path.join(carpeta_base, 'S2A_MSIL2A_20240914T152651_N0511_R025_T18NVK_20240914T222508.SAFE')

# Verifica si el archivo está en el subdirectorio
archivo_necesario = 'S2A_MSIL2A_20240914T152651_N0511_R025_T18NVK_20240914T222508-ql.jpg'
ruta_imagen = os.path.join(subcarpeta, archivo_necesario)

# Comprueba si la ruta existe
if os.path.exists(ruta_imagen):
    print(f"El archivo {ruta_imagen} existe y está listo para usarse.")
else:
    print(f"El archivo {archivo_necesario} no se encuentra en la ruta {subcarpeta}. Verifica el nombre y ubicación.")

import os
from PIL import Image
import torch

# Define la carpeta base en Google Drive
carpeta_base = '/content/drive/My Drive/Data/'

# Subcarpeta donde se encuentra el archivo
subcarpeta = os.path.join(carpeta_base, 'S2A_MSIL2A_20240914T152651_N0511_R025_T18NVK_20240914T222508.SAFE')

# Nombre del archivo que necesitas cargar
archivo_necesario = 'S2A_MSIL2A_20240914T152651_N0511_R025_T18NVK_20240914T222508-ql.jpg'

# Construir la ruta completa
ruta_imagen = os.path.join(subcarpeta, archivo_necesario)

# Verificar si la ruta existe
if not os.path.exists(ruta_imagen):
    print(f"El archivo no existe en la ruta: {ruta_imagen}")
    # Lista los archivos en la subcarpeta para confirmar los disponibles
    print("Archivos disponibles en la subcarpeta:")
    print(os.listdir(subcarpeta))
else:
    print(f"El archivo fue encontrado: {ruta_imagen}")

# Función para cargar y preprocesar la imagen
def cargar_y_preprocesar_imagen(ruta_imagen, transformacion):
    # Cargar la imagen
    imagen = Image.open(ruta_imagen).convert('RGB')

    # Aplicar transformaciones
    imagen_preprocesada = transformacion(imagen)

    # Añadir dimensión para el batch (torch espera un tensor de tamaño [batch, channels, height, width])
    imagen_preprocesada = imagen_preprocesada.unsqueeze(0)

    return imagen_preprocesada

# Solo proceder si la ruta existe
if os.path.exists(ruta_imagen):
    # Cargar y preprocesar la imagen
    imagen_preprocesada = cargar_y_preprocesar_imagen(ruta_imagen, transformacion_prueba)

    # Enviar la imagen al dispositivo (CPU o GPU)
    imagen_preprocesada = imagen_preprocesada.to(dispositivo)

    # Realizar la predicción
    modelo.eval()  # Asegurarse de que el modelo está en modo evaluación
    with torch.no_grad():
        salida = modelo(imagen_preprocesada)
        _, prediccion = torch.max(salida, 1)

    # Mostrar la clase predicha
    clase_predicha = nombres_clases[prediccion.item()]
    print(f"La clase predicha para la imagen es: {clase_predicha}")