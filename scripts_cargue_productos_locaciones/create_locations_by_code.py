#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear locaciones usando códigos específicos con el API de Kong RFID WMS
Autor: Kong RFID WMS Team
Fecha: 2025-08-15
"""

import requests
import json
import sys
import argparse
from typing import Dict, List, Optional
from urllib.parse import urljoin


class LocationCreatorByCode:
    """Clase para crear locaciones usando códigos específicos"""
    
    # Tipos de locación disponibles
    LOCATION_TYPES = {
        'O1': {'name': 'SHOWROOM', 'parent': 'STORE-M1'},
        'N1': {'name': 'STORE_WAREHOUSE', 'parent': 'STORE-M1'},
        'M1': {'name': 'STORE', 'parent': 'CITY-C1'},
        'K2': {'name': 'POSITION-BACK', 'parent': 'LEVEL-BACK-J2'},
        'K1': {'name': 'POSITION-FRONT', 'parent': 'LEVEL-FRONT-J1'},
        'J2': {'name': 'LEVEL-BACK', 'parent': 'RACK-BACK-I2'},
        'J1': {'name': 'LEVEL-FRONT', 'parent': 'RACK-FRONT-I1'},
        'I2': {'name': 'RACK-BACK', 'parent': 'BACK-H2'},
        'I1': {'name': 'RACK-FRONT', 'parent': 'FRONT-H1'},
        'H2': {'name': 'BACK', 'parent': 'ROW-G1'},
        'H1': {'name': 'FRONT', 'parent': 'ROW-G1'},
        'G1': {'name': 'ROW', 'parent': 'SALON-F1'},
        'F1': {'name': 'SALON', 'parent': 'WAREHOUSE-E1'},
        'E1': {'name': 'WAREHOUSE', 'parent': 'HOLDING-D1'},
        'D1': {'name': 'HOLDING', 'parent': 'CITY-C1'},
        'C1': {'name': 'CITY', 'parent': 'DEPARTMENT/STATE-B1'},
        'B1': {'name': 'DEPARTMENT/STATE', 'parent': 'COUNTRY-A1'},
        'A1': {'name': 'COUNTRY', 'parent': '-'}
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.api_url = None
        self.token = None
    
    def setup_session(self, api_url: str, token: str):
        """Configurar la sesión HTTP con URL base y token"""
        self.api_url = api_url.rstrip('/')
        self.token = token
        
        self.session.headers.update({
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Validar conectividad
        try:
            test_url = urljoin(f"{self.api_url}/", "inventory/locations/")
            response = self.session.get(test_url, params={'limit': 1})
            response.raise_for_status()
            print(f"✅ Conexión exitosa al API: {self.api_url}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión al API: {e}")
            return False
    
    def show_location_types(self):
        """Mostrar tabla de tipos de locación disponibles"""
        print("\n📍 TIPOS DE LOCACIÓN DISPONIBLES:")
        print("=" * 60)
        print(f"{'External ID':<12} {'Nombre':<20} {'Padre':<20}")
        print("-" * 60)
        
        for ext_id, info in self.LOCATION_TYPES.items():
            parent = info['parent'] if info['parent'] != '-' else 'Sin padre'
            print(f"{ext_id:<12} {info['name']:<20} {parent:<20}")
        print("=" * 60)
    
    def validate_location_type(self, type_external_id: str) -> bool:
        """Validar que el tipo de locación existe"""
        return type_external_id in self.LOCATION_TYPES
    
    def parse_location_codes(self, codes_input: str) -> List[Dict]:
        """Parsear los códigos de locación del input del usuario"""
        codes = [code.strip() for code in codes_input.split(',') if code.strip()]
        parsed_locations = []
        
        for code in codes:
            # Validar formato básico
            if not code or '-' not in code:
                raise ValueError(f"Código inválido: '{code}'. Debe tener formato como 'ON-D01-M01-N01-P01'")
            
            # Dividir el código para obtener parent_external_id y name
            parts = code.split('-')
            if len(parts) < 4:
                raise ValueError(f"Código inválido: '{code}'. Debe tener al menos 4 partes separadas por '-'")
            
            # El parent_external_id son todas las partes excepto la última
            parent_external_id = '-'.join(parts[:-1])
            name = code
            
            parsed_locations.append({
                'name': name,
                'display_name': name,
                'parent_external_id': parent_external_id,
                'original_code': code
            })
        
        return parsed_locations
    
    def get_user_input(self) -> Dict:
        """Obtener datos del usuario"""
        print("\n🏗️  CREADOR DE LOCACIONES POR CÓDIGOS")
        print("=" * 50)
        
        # URL del API
        api_url = input("🌐 URL del API (ej: https://api.kong-wms.com): ").strip()
        if not api_url:
            raise ValueError("La URL del API es requerida")
        
        # Token
        token = input("🔑 Token de autenticación: ").strip()
        if not token:
            raise ValueError("El token es requerido")
        
        # Configurar sesión
        if not self.setup_session(api_url, token):
            raise ValueError("No se pudo conectar al API")
        
        # Mostrar tipos disponibles
        self.show_location_types()
        
        # Tipo de locación
        type_external_id = input("\n📋 External ID del tipo de locación: ").strip().upper()
        if not self.validate_location_type(type_external_id):
            raise ValueError(f"Tipo de locación '{type_external_id}' no válido")
        
        # Customer ID
        try:
            customer_id = int(input("👤 Customer ID: ").strip())
            if customer_id <= 0:
                raise ValueError("El Customer ID debe ser mayor a 0")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("El Customer ID debe ser un número válido")
            raise
        
        # Códigos de locaciones
        print("\n📝 Ingrese los códigos de locaciones separados por comas")
        print("   Formato: ON-D01-M01-N01-P01, ON-D01-M01-N01-P02, ...")
        print("   Donde ON-D01-M01-N01 será el parent_external_id")
        print("   y ON-D01-M01-N01-P01 será el name y display_name")
        
        codes_input = input("\n🔢 Códigos de locaciones: ").strip()
        if not codes_input:
            raise ValueError("Los códigos de locaciones son requeridos")
        
        # Parsear códigos
        try:
            location_codes = self.parse_location_codes(codes_input)
        except ValueError as e:
            raise ValueError(f"Error en los códigos: {e}")
        
        if not location_codes:
            raise ValueError("No se encontraron códigos válidos")
        
        return {
            'type_external_id': type_external_id,
            'customer_id': customer_id,
            'location_codes': location_codes
        }
    
    def create_payloads(self, config: Dict) -> List[Dict]:
        """Crear los payloads para cada locación"""
        payloads = []
        
        print(f"\n📋 Creando payloads para {len(config['location_codes'])} locaciones:")
        
        for location_data in config['location_codes']:
            payload = {
                "type_external_id": config['type_external_id'],
                "customer_ids": [config['customer_id']],
                "parent_external_id": location_data['parent_external_id'],
                "name": location_data['name'],
                "display_name": location_data['display_name'],
                "is_active": True,
                "zone_type": ""
            }
            
            payloads.append(payload)
            print(f"  - {location_data['name']} (parent: {location_data['parent_external_id']})")
        
        return payloads
    
    def create_location(self, payload: Dict) -> Dict:
        """Crear una locación individual"""
        url = urljoin(f"{self.api_url}/", "inventory/locations/")
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json(),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            error_detail = "Error desconocido"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
            
            return {
                'success': False,
                'error': str(e),
                'error_detail': error_detail,
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def create_locations_batch(self, payloads: List[Dict]) -> Dict:
        """Crear locaciones en lote"""
        results = {
            'total': len(payloads),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        print(f"\n🚀 Iniciando creación de {len(payloads)} locaciones...")
        print("-" * 60)
        
        for i, payload in enumerate(payloads, 1):
            location_name = payload['name']
            print(f"[{i:02d}/{len(payloads):02d}] Creando: {location_name}...", end=" ")
            
            result = self.create_location(payload)
            
            if result['success']:
                print("✅ ÉXITO")
                results['success'] += 1
                results['details'].append({
                    'name': location_name,
                    'status': 'success',
                    'id': result['data'].get('id'),
                    'parent_external_id': payload['parent_external_id']
                })
            else:
                print("❌ ERROR")
                results['failed'] += 1
                results['details'].append({
                    'name': location_name,
                    'status': 'failed',
                    'error': result['error'],
                    'error_detail': result['error_detail'],
                    'parent_external_id': payload['parent_external_id']
                })
                
                # Mostrar detalle del error
                print(f"     Error: {result['error']}")
                if result['error_detail']:
                    print(f"     Detalle: {result['error_detail']}")
        
        return results
    
    def show_summary(self, results: Dict):
        """Mostrar resumen de resultados"""
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE CREACIÓN DE LOCACIONES")
        print("=" * 60)
        print(f"Total de locaciones: {results['total']}")
        print(f"✅ Creadas exitosamente: {results['success']}")
        print(f"❌ Errores: {results['failed']}")
        
        if results['failed'] > 0:
            print(f"\n🔍 DETALLES DE ERRORES:")
            print("-" * 40)
            for detail in results['details']:
                if detail['status'] == 'failed':
                    print(f"• {detail['name']}: {detail['error']}")
                    if detail['error_detail']:
                        print(f"  Detalle: {detail['error_detail']}")
        
        if results['success'] > 0:
            print(f"\n✅ LOCACIONES CREADAS EXITOSAMENTE:")
            print("-" * 40)
            for detail in results['details']:
                if detail['status'] == 'success':
                    print(f"• {detail['name']} (ID: {detail['id']}, Parent: {detail['parent_external_id']})")
        
        print("=" * 60)
    
    def run_interactive(self):
        """Ejecutar modo interactivo"""
        try:
            # Obtener configuración del usuario
            config = self.get_user_input()
            
            # Crear payloads
            payloads = self.create_payloads(config)
            
            # Mostrar vista previa
            print(f"\n📋 VISTA PREVIA DE LOCACIONES A CREAR:")
            print("-" * 50)
            print(f"Tipo: {config['type_external_id']} ({self.LOCATION_TYPES[config['type_external_id']]['name']})")
            print(f"Customer: {config['customer_id']}")
            print(f"Cantidad: {len(config['location_codes'])}")
            print("\nLocaciones que se crearán:")
            for i, location_data in enumerate(config['location_codes'][:10], 1):  # Mostrar solo las primeras 10
                print(f"  {i}. {location_data['name']} (parent: {location_data['parent_external_id']})")
            
            if len(config['location_codes']) > 10:
                print(f"  ... y {len(config['location_codes']) - 10} más")
            
            # Confirmar
            confirm = input(f"\n¿Proceder con la creación? (s/N): ").strip().lower()
            if confirm not in ['s', 'si', 'sí', 'y', 'yes']:
                print("❌ Operación cancelada por el usuario")
                return
            
            # Crear locaciones
            results = self.create_locations_batch(payloads)
            
            # Mostrar resumen
            self.show_summary(results)
            
        except KeyboardInterrupt:
            print("\n\n❌ Operación cancelada por el usuario")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    def run_batch(self, args):
        """Ejecutar modo batch (por argumentos)"""
        try:
            # Validar argumentos
            if not self.validate_location_type(args.type_external_id):
                raise ValueError(f"Tipo de locación '{args.type_external_id}' no válido")
            
            # Configurar sesión
            if not self.setup_session(args.api_url, args.token):
                raise ValueError("No se pudo conectar al API")
            
            # Parsear códigos
            try:
                location_codes = self.parse_location_codes(args.location_codes)
            except ValueError as e:
                raise ValueError(f"Error en los códigos: {e}")
            
            # Preparar configuración
            config = {
                'type_external_id': args.type_external_id,
                'customer_id': args.customer_id,
                'location_codes': location_codes
            }
            
            # Crear payloads
            payloads = self.create_payloads(config)
            
            # Crear locaciones
            results = self.create_locations_batch(payloads)
            
            # Mostrar resumen
            self.show_summary(results)
            
            # Exit code según resultados
            sys.exit(0 if results['failed'] == 0 else 1)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Crear locaciones usando códigos específicos con el API de Kong RFID WMS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  Modo interactivo:
    python3 create_locations_by_code.py

  Modo batch:
    python3 create_locations_by_code.py \\
        --api-url https://api.kong-wms.com \\
        --token your_api_token \\
        --type-external-id K1 \\
        --customer-id 1 \\
        --location-codes "ON-D01-M01-N01-P01,ON-D01-M01-N01-P02,ON-D01-M01-N01-P03"

Formato de códigos:
  - Cada código debe seguir el patrón: PREFIX-PART1-PART2-PART3-POSITION
  - Ejemplo: ON-D01-M01-N01-P01
  - parent_external_id será: ON-D01-M01-N01
  - name y display_name será: ON-D01-M01-N01-P01

Tipos de locación disponibles:
  O1, N1, M1, K2, K1, J2, J1, I2, I1, H2, H1, G1, F1, E1, D1, C1, B1, A1
        """
    )
    
    # Argumentos opcionales para modo batch
    parser.add_argument('--api-url', help='URL del API')
    parser.add_argument('--token', help='Token de autenticación')
    parser.add_argument('--type-external-id', help='External ID del tipo de locación')
    parser.add_argument('--customer-id', type=int, help='Customer ID')
    parser.add_argument('--location-codes', help='Códigos de locaciones separados por comas')
    parser.add_argument('--list-types', action='store_true', help='Mostrar tipos de locación disponibles')
    
    args = parser.parse_args()
    
    creator = LocationCreatorByCode()
    
    # Si solo quiere ver los tipos
    if args.list_types:
        creator.show_location_types()
        return
    
    # Detectar modo de ejecución
    batch_args = [args.api_url, args.token, args.type_external_id, 
                  args.customer_id, args.location_codes]
    
    if all(arg is not None for arg in batch_args):
        # Modo batch - todos los argumentos requeridos están presentes
        creator.run_batch(args)
    else:
        # Modo interactivo
        if any(arg is not None for arg in batch_args):
            print("⚠️  Algunos argumentos proporcionados pero no todos los requeridos.")
            print("    Se ejecutará en modo interactivo.\n")
        creator.run_interactive()


if __name__ == "__main__":
    main()
