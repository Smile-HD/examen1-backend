este es el contexto:
"
Plataforma Inteligente de Atención de Emergencias Vehiculares
1. DESCRIPCIÓN DEL PROBLEMA
En entornos urbanos y carreteras, los conductores frecuentemente enfrentan situaciones
imprevistas como fallas mecánicas, pinchazos de llantas, problemas de batería,
sobrecalentamiento del motor o accidentes leves, perder la llave del vehículo, dejar llave
dentro el vehículo y otros.
En muchos casos, el proceso de conseguir ayuda es ineficiente, lento y poco confiable.
Actualmente, las alternativas existentes presentan limitaciones como:
 dependencia de llamadas telefónicas
 falta de información clara sobre el problema
 tiempos de respuesta impredecibles
 dificultad para identificar el proveedor adecuado
 ausencia de trazabilidad del servicio
Por otro lado, los talleres mecánicos no cuentan con una plataforma estructurada que les
permita:
 recibir solicitudes de manera organizada
 evaluar rápidamente la naturaleza del problema
 priorizar casos
 optimizar la asignación de recursos
La plataforma debe integrar múltiples fuentes de información (imágenes, audio,
ubicación) para asistir en la clasificación automática del incidente y facilitar la toma de
decisiones.
2. OBJETIVO GENERAL
Desarrollar una plataforma inteligente de atención de emergencias vehiculares que
permita conectar usuarios con talleres mecánicos mediante el análisis automatizado de
incidentes utilizando datos multimodales (imagen, audio, texto y geolocalización),
optimizando el proceso de diagnóstico preliminar, priorización y asignación del servicio.
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
2
3. OBJETIVOS ESPECÍFICOS
 Diseñar una arquitectura basada en servicios que soporte procesamiento en
tiempo real.
 Implementar una aplicación móvil para usuarios que permita reportar
emergencias vehiculares.
 Diseñar una aplicación web para talleres que gestione solicitudes y operaciones.
 Integrar mecanismos de geolocalización para ubicar incidentes y proveedores.
 Incorporar módulos de inteligencia artificial para:
o transcripción de audio
o clasificación de incidentes
o análisis básico de imágenes
 Diseñar un sistema de priorización de emergencias.
 Implementar un mecanismo de asignación inteligente de talleres.
 Gestionar notificaciones en tiempo real (push).
 Mantener trazabilidad completa de cada incidente.
4. ALCANCE Y FUNCIONALIDADES DEL SISTEMA
4.1 Aplicación móvil (Cliente)
El usuario deberá poder:
Los clientes se deben registrar en la aplicación, como también registrar sus vehículos
Registro de emergencia
 enviar ubicación en tiempo real
 adjuntar fotos del vehículo
 enviar audio describiendo el problema
 ingresar texto adicional opcional
Gestión de solicitudes
 visualizar estado de su solicitud:
o pendiente
o en proceso
o atendido
 ver taller asignado
 ver tiempo estimado de llegada
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
3

Interacción
 recibir notificaciones push
 comunicarse con el taller (opcional)
El cliente debe realizar los pagos correspondientes desde la aplicación

4.2 Aplicación web (Talleres)
Los Talleres se deben registrar para que sean los que provean el servicio de asistencia a
los clientes que lo soliciten, para esto un taller puede tener uno o más técnicos quienes
serán los asignados para asistir a un cliente
Cuando un taller recibe una alerta de asistencia revisa el lugar donde se encuentran sus
técnicos y disponibilidad para asignarle la orden correspondiente según el tipo de
percance y ubicación del cliente que solicita asistencia
El taller debe pagar un porcentaje (10%) del precio cobrado a la plataforma como
comisión
Los talleres deberán poder:
Gestión de solicitudes
 visualizar solicitudes disponibles
 ver información estructurada del incidente
 aceptar o rechazar solicitudes
Operación
 actualizar estado del servicio
 gestionar disponibilidad
 visualizar historial de atenciones
Información enriquecida (IA)
 ver resumen automático del incidente
 ver clasificación del problema
 ver nivel de prioridad
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
4
4.3 Backend (FastAPI)
El sistema backend deberá gestionar:
 autenticación y autorización
 gestión de usuarios y talleres
 gestión de incidentes
 procesamiento de datos
 integración con módulos de IA
 motor de asignación
 sistema de notificaciones
 APIs REST
4.4 Base de datos (PostgreSQL)
El modelo de datos deberá contemplar:
 usuarios
 talleres
 vehículos
 incidentes
 evidencias (imagen, audio, texto)
 estados del servicio
 historial
 métricas
Debe considerar:
 integridad de datos
 relaciones complejas
 trazabilidad
4.5 Módulos de Inteligencia Artificial
1. Procesamiento de audio
 conversión de audio a texto
 extracción de información relevante


Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
5
2. Clasificación de incidentes (Imágenes a través de fotos lo clasifica, visión artificial)
 categorización automática del problema:
o batería
o llanta
o choque
o motor
o otros
3. Análisis de imágenes (básico)
 identificación de daños visibles
 apoyo en la clasificación del incidente
4. Generación de resumen
 creación automática de una ficha estructurada del incidente
4.6 Sistema de asignación inteligente
Debe considerar:
 ubicación del incidente
 tipo de problema
 disponibilidad del taller
 capacidad del taller
 distancia
 prioridad del caso
El sistema debe generar:
 lista de talleres candidatos
 selección del más adecuado
4.7 Notificaciones
 notificaciones push al cliente
 notificaciones a talleres
 actualizaciones en tiempo real


Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
6
5. CARACTERÍSTICAS DEL SISTEMA
 integración de múltiples fuentes de datos
 uso de inteligencia artificial aplicada al flujo del sistema
 diseño de interfaces centrado en experiencia de usuario
6. STACK TECNOLOGICO
 frontend web: Angular
 backend: FastAPI (framework) - phyton
 base de datos: PostgreSQL
 aplicación móvil: Flutter

7. EJEMPLOS DE SITUACIONES DE USO

Caso 1: Problema de batería
Un usuario se encuentra en un estacionamiento y su vehículo no enciende.
Envía:
 ubicación
 audio indicando que el auto no responde
 foto del tablero
El sistema:
 transcribe el audio
 clasifica como “problema de batería”
 asigna prioridad media
 sugiere talleres con servicio de auxilio eléctrico
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
7
Caso 2: Pinchazo de llanta
El usuario reporta:
 foto de llanta dañada
 ubicación en carretera
El sistema:
 detecta posible pinchazo
 clasifica como incidente leve
 asigna prioridad media
 sugiere talleres cercanos con servicio móvil
Caso 3: Accidente leve
El usuario envía:
 múltiples fotos
 audio indicando choque
El sistema:
 detecta daño visible
 clasifica como choque
 asigna prioridad alta
 sugiere talleres con capacidad de remolque
Caso 4: Situación ambigua
El usuario envía información poco clara.
El sistema:
 clasifica como “incierto”
 solicita más información
 permite intervención manual
8. CONSIDERACIONES IMPORTANTES
 La IA no debe considerarse un módulo aislado, sino parte del flujo principal.
 El sistema debe manejar incertidumbre (no todos los casos serán claros).
 Se espera que los estudiantes tomen decisiones de diseño justificadas.

"
con eso en mente responde a cada chat o pregunta que te haga
"
Plataforma Inteligente de Atención de Emergencias Vehiculares
1. DESCRIPCIÓN DEL PROBLEMA
En entornos urbanos y carreteras, los conductores frecuentemente enfrentan situaciones
imprevistas como fallas mecánicas, pinchazos de llantas, problemas de batería,
sobrecalentamiento del motor o accidentes leves, perder la llave del vehículo, dejar llave
dentro el vehículo y otros.
En muchos casos, el proceso de conseguir ayuda es ineficiente, lento y poco confiable.
Actualmente, las alternativas existentes presentan limitaciones como:
 dependencia de llamadas telefónicas
 falta de información clara sobre el problema
 tiempos de respuesta impredecibles
 dificultad para identificar el proveedor adecuado
 ausencia de trazabilidad del servicio
Por otro lado, los talleres mecánicos no cuentan con una plataforma estructurada que les
permita:
 recibir solicitudes de manera organizada
 evaluar rápidamente la naturaleza del problema
 priorizar casos
 optimizar la asignación de recursos
La plataforma debe integrar múltiples fuentes de información (imágenes, audio,
ubicación) para asistir en la clasificación automática del incidente y facilitar la toma de
decisiones.
2. OBJETIVO GENERAL
Desarrollar una plataforma inteligente de atención de emergencias vehiculares que
permita conectar usuarios con talleres mecánicos mediante el análisis automatizado de
incidentes utilizando datos multimodales (imagen, audio, texto y geolocalización),
optimizando el proceso de diagnóstico preliminar, priorización y asignación del servicio.
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
2
3. OBJETIVOS ESPECÍFICOS
 Diseñar una arquitectura basada en servicios que soporte procesamiento en
tiempo real.
 Implementar una aplicación móvil para usuarios que permita reportar
emergencias vehiculares.
 Diseñar una aplicación web para talleres que gestione solicitudes y operaciones.
 Integrar mecanismos de geolocalización para ubicar incidentes y proveedores.
 Incorporar módulos de inteligencia artificial para:
o transcripción de audio
o clasificación de incidentes
o análisis básico de imágenes
 Diseñar un sistema de priorización de emergencias.
 Implementar un mecanismo de asignación inteligente de talleres.
 Gestionar notificaciones en tiempo real (push).
 Mantener trazabilidad completa de cada incidente.
4. ALCANCE Y FUNCIONALIDADES DEL SISTEMA
4.1 Aplicación móvil (Cliente)
El usuario deberá poder:
Los clientes se deben registrar en la aplicación, como también registrar sus vehículos
Registro de emergencia
 enviar ubicación en tiempo real
 adjuntar fotos del vehículo
 enviar audio describiendo el problema
 ingresar texto adicional opcional
Gestión de solicitudes
 visualizar estado de su solicitud:
o pendiente
o en proceso
o atendido
 ver taller asignado
 ver tiempo estimado de llegada
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
3

Interacción
 recibir notificaciones push
 comunicarse con el taller (opcional)
El cliente debe realizar los pagos correspondientes desde la aplicación

4.2 Aplicación web (Talleres)
Los Talleres se deben registrar para que sean los que provean el servicio de asistencia a
los clientes que lo soliciten, para esto un taller puede tener uno o más técnicos quienes
serán los asignados para asistir a un cliente
Cuando un taller recibe una alerta de asistencia revisa el lugar donde se encuentran sus
técnicos y disponibilidad para asignarle la orden correspondiente según el tipo de
percance y ubicación del cliente que solicita asistencia
El taller debe pagar un porcentaje (10%) del precio cobrado a la plataforma como
comisión
Los talleres deberán poder:
Gestión de solicitudes
 visualizar solicitudes disponibles
 ver información estructurada del incidente
 aceptar o rechazar solicitudes
Operación
 actualizar estado del servicio
 gestionar disponibilidad
 visualizar historial de atenciones
Información enriquecida (IA)
 ver resumen automático del incidente
 ver clasificación del problema
 ver nivel de prioridad
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
4
4.3 Backend (FastAPI)
El sistema backend deberá gestionar:
 autenticación y autorización
 gestión de usuarios y talleres
 gestión de incidentes
 procesamiento de datos
 integración con módulos de IA
 motor de asignación
 sistema de notificaciones
 APIs REST
4.4 Base de datos (PostgreSQL)
El modelo de datos deberá contemplar:
 usuarios
 talleres
 vehículos
 incidentes
 evidencias (imagen, audio, texto)
 estados del servicio
 historial
 métricas
Debe considerar:
 integridad de datos
 relaciones complejas
 trazabilidad
4.5 Módulos de Inteligencia Artificial
1. Procesamiento de audio
 conversión de audio a texto
 extracción de información relevante


Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
5
2. Clasificación de incidentes (Imágenes a través de fotos lo clasifica, visión artificial)
 categorización automática del problema:
o batería
o llanta
o choque
o motor
o otros
3. Análisis de imágenes (básico)
 identificación de daños visibles
 apoyo en la clasificación del incidente
4. Generación de resumen
 creación automática de una ficha estructurada del incidente
4.6 Sistema de asignación inteligente
Debe considerar:
 ubicación del incidente
 tipo de problema
 disponibilidad del taller
 capacidad del taller
 distancia
 prioridad del caso
El sistema debe generar:
 lista de talleres candidatos
 selección del más adecuado
4.7 Notificaciones
 notificaciones push al cliente
 notificaciones a talleres
 actualizaciones en tiempo real


Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
6
5. CARACTERÍSTICAS DEL SISTEMA
 integración de múltiples fuentes de datos
 uso de inteligencia artificial aplicada al flujo del sistema
 diseño de interfaces centrado en experiencia de usuario
6. STACK TECNOLOGICO
 frontend web: Angular
 backend: FastAPI (framework) - phyton
 base de datos: PostgreSQL
 aplicación móvil: Flutter

7. EJEMPLOS DE SITUACIONES DE USO

Caso 1: Problema de batería
Un usuario se encuentra en un estacionamiento y su vehículo no enciende.
Envía:
 ubicación
 audio indicando que el auto no responde
 foto del tablero
El sistema:
 transcribe el audio
 clasifica como “problema de batería”
 asigna prioridad media
 sugiere talleres con servicio de auxilio eléctrico
Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar
7
Caso 2: Pinchazo de llanta
El usuario reporta:
 foto de llanta dañada
 ubicación en carretera
El sistema:
 detecta posible pinchazo
 clasifica como incidente leve
 asigna prioridad media
 sugiere talleres cercanos con servicio móvil
Caso 3: Accidente leve
El usuario envía:
 múltiples fotos
 audio indicando choque
El sistema:
 detecta daño visible
 clasifica como choque
 asigna prioridad alta
 sugiere talleres con capacidad de remolque
Caso 4: Situación ambigua
El usuario envía información poco clara.
El sistema:
 clasifica como “incierto”
 solicita más información
 permite intervención manual
8. CONSIDERACIONES IMPORTANTES
 La IA no debe considerarse un módulo aislado, sino parte del flujo principal.
 El sistema debe manejar incertidumbre (no todos los casos serán claros).
 Se espera que los estudiantes tomen decisiones de diseño justificadas.

Examen 1 Sistemas 2 - S1-26 MSc. Ing. Angélica Garzón Cuéllar

"
con eso en mente responde a cada chat o pregunta que te haga

Informacion del proyecto a realizar:
"Perfil 
El presente proyecto consiste en el desarrollo de una Plataforma Inteligente de Atención de Emergencias Vehiculares, orientada a brindar asistencia rápida, eficiente y automatizada a conductores que presenten fallas mecánicas o incidentes en la vía pública.
La plataforma integrará tecnologías modernas como aplicaciones móviles, servicios web y herramientas de inteligencia artificial, permitiendo analizar información proporcionada por el usuario (texto, audio, imágenes y ubicación geográfica) para identificar el tipo de emergencia y asignar de manera automática el taller o servicio técnico más adecuado.
Este sistema busca optimizar los tiempos de respuesta, mejorar la experiencia del usuario y facilitar la gestión de servicios mecánicos, incorporando además funcionalidades como seguimiento en tiempo real, historial de incidentes y evaluación del servicio recibido.
Introducción 
En la actualidad, el uso de vehículos se ha convertido en un elemento esencial para el desarrollo de actividades diarias, tanto en el ámbito personal como laboral. Sin embargo, esta dependencia también conlleva una serie de riesgos asociados, especialmente cuando se presentan fallas mecánicas inesperadas, accidentes leves o situaciones de emergencia en la vía pública.
Uno de los principales problemas que enfrentan los conductores es la falta de acceso inmediato a servicios de asistencia confiables, lo cual genera retrasos, estrés e incluso situaciones de inseguridad. En muchos casos, la búsqueda de ayuda se realiza de manera manual, mediante llamadas telefónicas o consultas informales, lo que dificulta obtener una solución rápida y adecuada.
A pesar de los avances tecnológicos en otras áreas, la atención de emergencias vehiculares aún presenta limitaciones importantes, como la ausencia de sistemas automatizados, la falta de integración entre usuarios y talleres mecánicos, y la carencia de herramientas que permitan un diagnóstico preliminar eficiente del problema.
En este contexto, la incorporación de tecnologías emergentes como aplicaciones móviles, servicios web e inteligencia artificial representa una oportunidad significativa para mejorar la gestión de estas situaciones. La capacidad de procesar información en tiempo real, analizar datos mediante algoritmos inteligentes y automatizar la toma de decisiones permite optimizar los procesos de atención y reducir significativamente los tiempos de respuesta.
El presente proyecto propone el desarrollo de una Plataforma Inteligente de Atención de Emergencias Vehiculares, la cual permitirá a los usuarios reportar incidentes mediante diferentes tipos de entrada (texto, audio, imágenes y ubicación geográfica), los cuales serán procesados por un sistema inteligente capaz de identificar el tipo de problema y asignar automáticamente el servicio mecánico más adecuado.
Además, la plataforma no solo se enfocará en la atención de emergencias, sino también en la mejora continua del servicio mediante el registro histórico de incidentes, evaluación de talleres y optimización del proceso de asignación. De esta manera, se busca ofrecer una solución tecnológica innovadora que contribuya a una atención más rápida, eficiente y segura en situaciones vehiculares.


Objetivo General 
Desarrollar una plataforma inteligente de atención de emergencias vehiculares que permita gestionar, analizar y resolver incidentes de manera eficiente mediante el uso de tecnologías móviles, web e inteligencia artificial, optimizando la asignación de servicios mecánicos y reduciendo significativamente los tiempos de respuesta.
Objetivos Específicos

Analizar los requerimientos del sistema para la correcta identificación de las necesidades de los usuarios y talleres mecánicos.
Diseñar una aplicación móvil intuitiva que permita a los usuarios reportar emergencias vehiculares mediante diferentes tipos de entrada de información (texto, audio, imágenes y ubicación geográfica).
Implementar un módulo de inteligencia artificial capaz de interpretar y clasificar los incidentes vehiculares en función de la información proporcionada.
Desarrollar un sistema de asignación automática que seleccione el taller mecánico más adecuado considerando factores como proximidad, disponibilidad, especialización y prioridad del incidente.
Crear una plataforma web para talleres que permita la gestión eficiente de solicitudes, incluyendo la aceptación, seguimiento y finalización de servicios.
Diseñar e implementar una base de datos estructurada que permita el almacenamiento seguro y organizado de la información del sistema.
Implementar un sistema de notificaciones en tiempo real que mantenga informado al usuario sobre el estado de su solicitud.
Incorporar un sistema de evaluación y retroalimentación del servicio para mejorar la calidad de atención.
Desarrollar mecanismos de seguridad que protejan la información de los usuarios y garanticen la confiabilidad del sistema. 

Descripción del problema
En la actualidad, los conductores que enfrentan emergencias vehiculares carecen de herramientas eficientes que les permitan acceder de manera rápida y confiable a servicios de asistencia mecánica. Esta situación se ve agravada por la falta de sistemas centralizados que integren información sobre talleres disponibles, tipos de servicios ofrecidos y tiempos de respuesta.
Entre las principales dificultades que enfrentan los usuarios se encuentran:
La falta de conocimiento sobre talleres cercanos o disponibles en el momento de la emergencia.
La demora en la atención debido a procesos manuales de búsqueda y contacto.
La dificultad para describir con precisión el problema mecánico, lo que puede generar diagnósticos incorrectos.
La ausencia de seguimiento en tiempo real del servicio solicitado.
La falta de confianza en la calidad del servicio ofrecido.
Estas problemáticas no solo generan incomodidad y pérdida de tiempo, sino que también pueden poner en riesgo la seguridad de los conductores, especialmente en situaciones críticas.
Por lo tanto, resulta necesario implementar una solución tecnológica que permita automatizar y optimizar la atención de emergencias vehiculares, mejorando la comunicación entre usuarios y talleres, y garantizando una respuesta más rápida y eficiente.







Alcance 
El presente proyecto tiene como alcance el diseño y desarrollo de un sistema integral orientado a la atención de emergencias vehiculares, el cual estará compuesto por múltiples componentes tecnológicos que trabajarán de manera conjunta para garantizar su funcionamiento.
La solución incluirá el desarrollo de una aplicación móvil para usuarios, una plataforma web para talleres mecánicos y un sistema backend encargado de la gestión de la lógica del negocio, procesamiento de datos y comunicación entre los distintos módulos del sistema.
Dentro del alcance funcional del sistema se contemplan las siguientes características:
Gestión de usuarios y vehículos
El sistema permitirá el registro, autenticación y administración de cuentas de usuario, así como la asociación de uno o más vehículos a cada usuario. Asimismo, se contemplará la actualización de datos personales y la gestión de la información relacionada con los vehículos registrados
Gestión de talleres mecánicos
Los talleres podrán registrarse en la plataforma y administrar la información relacionada con los servicios que ofrecen. Además, podrán gestionar su disponibilidad operativa, visualizar solicitudes de atención y tomar decisiones respecto a la aceptación o rechazo de las mismas
Reporte de emergencias vehiculares
Los usuarios podrán reportar incidentes en tiempo real mediante el envío de información multimodal, incluyendo descripciones en texto, notas de voz, imágenes del problema y su ubicación geográfica. Esta información permitirá una mejor comprensión del incidente desde etapas tempranas
Procesamiento inteligente de la información
El sistema incorporará mecanismos de inteligencia artificial para analizar la información proporcionada por el usuario, permitiendo la clasificación automática del tipo de emergencia y la generación de un diagnóstico preliminar que facilite la toma de decisiones.
Asignación inteligente de servicios
A partir del análisis del incidente, el sistema realizará la selección automática del taller más adecuado, considerando factores como la ubicación del usuario, el tipo de problema, la disponibilidad del taller y el nivel de prioridad del incidente.
Seguimiento y notificaciones
El sistema permitirá a los usuarios visualizar el estado de su solicitud en diferentes etapas (pendiente, en proceso y finalizado), además de recibir notificaciones en tiempo real sobre el progreso del servicio, información del técnico asignado y el tiempo estimado de llegada.
Historial y evaluación
Se mantendrá un registro completo de las emergencias atendidas, incluyendo cada una de las etapas del proceso. Además, los usuarios podrán evaluar el servicio recibido, permitiendo la generación de métricas y reportes orientados a la mejora continua del sistema
Comunicación entre usuario y taller
Se habilitará un mecanismo de comunicación entre el usuario y el taller asignado, con el objetivo de facilitar la coordinación del servicio y mejorar la atención durante el proceso.
Gestión de pagos y comisiones
El sistema permitirá la realización de pagos por parte del usuario a través de la aplicación móvil, así como la gestión de comisiones asociadas al servicio, donde el taller deberá abonar un porcentaje del valor de la atención a la plataforma.

Fundamentación Teórica 
 El taller mecánico como sistema de servicios
El taller mecánico puede entenderse, desde una perspectiva teórica, como un sistema de prestación de servicios técnicos orientado a la solución de problemas vehiculares. A diferencia de los sistemas productivos tradicionales, donde se fabrican bienes tangibles, el taller ofrece un servicio cuyo valor radica en la capacidad de diagnosticar, intervenir y restaurar el funcionamiento de un vehículo.
En este sentido, el funcionamiento de un taller no se limita únicamente a la reparación, sino que implica un proceso estructurado que inicia con la identificación de una necesidad por parte del cliente y culmina con la resolución del problema. Este proceso incluye la recepción del caso, el diagnóstico técnico, la determinación del tipo de intervención requerida y la ejecución del servicio correspondiente. Cada una de estas etapas requiere conocimiento especializado, recursos técnicos y capacidad de toma de decisiones.
La propuesta del sistema introduce una transformación significativa al integrar al taller dentro de un entorno digital estructurado, donde deja de ser un ente aislado y pasa a formar parte de una red interconectada de servicios.
Naturaleza y organización de los servicios mecánicos
Los servicios ofrecidos por un taller mecánico no son homogéneos, sino que responden a diferentes necesidades del vehículo y del contexto en el que se presenta la falla. Desde un enfoque teórico, estos servicios pueden entenderse como respuestas técnicas a distintos tipos de problemas, los cuales varían en complejidad, urgencia y requerimientos operativos.
En primer lugar, existen los servicios orientados a la prevención de fallas, cuyo objetivo es mantener el vehículo en condiciones óptimas de funcionamiento. Estos servicios se caracterizan por ser planificados y periódicos, y aunque no están directamente relacionados con situaciones de emergencia, constituyen una base importante en el historial del vehículo y en la reducción de incidentes futuros.
Por otro lado, se encuentran los servicios correctivos, que surgen cuando el vehículo ya presenta una falla. En este caso, el taller actúa de manera reactiva, identificando el origen del problema y aplicando las soluciones necesarias para restablecer el funcionamiento. Este tipo de servicios requiere un diagnóstico más detallado y, en muchos casos, implica un mayor tiempo de intervención.
Dentro de esta clasificación, adquieren especial relevancia los servicios de emergencia vehicular, los cuales constituyen el núcleo del sistema propuesto. Estos servicios se diferencian por su carácter urgente y por ocurrir, generalmente, fuera del entorno controlado del taller, como en carreteras o espacios públicos. Situaciones como una batería descargada, un neumático pinchado o un accidente leve requieren una respuesta inmediata, lo que introduce variables adicionales como la ubicación del cliente, la disponibilidad del técnico y el tiempo de desplazamiento.
Relación entre fallas vehiculares y servicios técnicos
Un aspecto fundamental en la comprensión del funcionamiento de los talleres es la relación directa que existe entre las fallas del vehículo y los servicios que se deben aplicar. En términos teóricos, esta relación puede entenderse como un proceso de mapeo entre un problema identificado y una solución técnica adecuada.
En un entorno tradicional, este proceso depende completamente del conocimiento y experiencia del técnico, quien interpreta los síntomas presentados por el vehículo y determina la intervención necesaria. Sin embargo, este enfoque puede ser subjetivo y variar entre distintos profesionales.
El sistema propuesto introduce un cambio importante al intentar estructurar y automatizar parcialmente este proceso mediante el uso de tecnologías de inteligencia artificial. A partir de la información proporcionada por el usuario, ya sea en forma de texto, imágenes o audio, el sistema realiza un análisis preliminar que permite clasificar el tipo de incidente y sugerir el servicio más adecuado. De esta manera, se reduce la incertidumbre inicial y se facilita la toma de decisiones tanto para el sistema como para el taller.
Clasificación del sistema propuesto
Desde el punto de vista de los sistemas de información, la plataforma desarrollada puede clasificarse como un sistema híbrido que integra múltiples enfoques.
Por un lado, funciona como un sistema transaccional, ya que gestiona operaciones básicas como el registro de usuarios, la creación de solicitudes y la asignación de servicios. Estas operaciones requieren rapidez y confiabilidad, ya que se ejecutan en tiempo real.
Al mismo tiempo, el sistema cumple una función de soporte a la toma de decisiones, debido a que incorpora mecanismos que ayudan a determinar aspectos clave como la prioridad de un incidente o la selección del taller más adecuado. Este componente introduce un nivel de inteligencia en el sistema, permitiendo optimizar la asignación de recursos.
Asimismo, se trata de un sistema distribuido, dado que sus componentes se encuentran separados pero interconectados, incluyendo la aplicación móvil, la aplicación web, el backend y los módulos de inteligencia artificial. Esta distribución permite que el sistema sea accesible desde diferentes dispositivos y ubicaciones.
Otra característica importante es su naturaleza en tiempo real, ya que la información fluye de manera inmediata entre los distintos actores del sistema. Esto es esencial en el contexto de emergencias vehiculares, donde los tiempos de respuesta son críticos.
Finalmente, el sistema puede considerarse inteligente, debido a la integración de técnicas de inteligencia artificial que permiten analizar información, clasificar incidentes y generar resúmenes automáticos, mejorando así la eficiencia del proceso.

Parte II – Proceso de desarrollo 
Flujo de Trabajo: Captura de Requisitos 
IDENTIFICAR ACTORES Y CASOS DE USO
ACTORES
Cliente: Es quien tiene el problema con el vehículo.
Taller: Es la entidad que ofrece el servicio.
Técnico: Es quien realmente va al lugar.
Administrador: Controla la plataforma.
Sistema: Es la Inteligencia artificial.

CASOS DE USO
CU1. Registrar USuario
CU2. Iniciar sesión
CU3. Registrar vehículo
CU4. Reportar emergencia 
CU5. Adjuntar información de incidente
CU6. Consultar estado de solicitud 
CU7. Realizar pago
CU8. Procesar incidente
CU9. Priorizar incidente
CU10. Asignar taller
CU11. Gestionar solicitudes
CU12. Asignar técnico
CU13. Gestionar disponibilidad
CU14. Consultar historial
CU15. Consultar asignaciones
CU16. Consultar ubicación del cliente
CU17. Actualizar estado del servicio
CU18. Enviar notificaciones
CU19. Recibir notificaciones 
CU20. Gestionar usuarios y talleres
CU21. Supervisar operaciones
CU22. Gestionar comisiones
CU23. Registrar unidad de servicio
"
