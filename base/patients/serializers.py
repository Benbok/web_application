from rest_framework import serializers
from .models import Patient, PatientContact, PatientAddress, PatientDocument


class PatientContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientContact
        fields = ['phone', 'email']


class PatientAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAddress
        fields = ['registration_address']


class PatientDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDocument
        fields = ['document_type', 'document_number']


class PatientSerializer(serializers.ModelSerializer):
    contact = PatientContactSerializer()
    address = PatientAddressSerializer()
    document = PatientDocumentSerializer()

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_type',
            'parents',
            'last_name',
            'first_name',
            'middle_name',
            'birth_date',
            'gender',
            'contact',
            'address',
            'document'
        ]

    def create(self, validated_data):
        contact_data = validated_data.pop('contact')
        address_data = validated_data.pop('address')
        document_data = validated_data.pop('document')
        patient = Patient.objects.create(**validated_data)
        PatientContact.objects.create(patient=patient, **contact_data)
        PatientAddress.objects.create(patient=patient, **address_data)
        PatientDocument.objects.create(patient=patient, **document_data)
        return patient

    def update(self, instance, validated_data):
        contact_data = validated_data.pop('contact', {})
        address_data = validated_data.pop('address', {})
        document_data = validated_data.pop('document', {})

        # Обновление полей пациента
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Обновляем или создаем вложенные объекты
        if hasattr(instance, 'contact'):
            for attr, value in contact_data.items():
                setattr(instance.contact, attr, value)
            instance.contact.save()
        else:
            PatientContact.objects.create(patient=instance, **contact_data)

        if hasattr(instance, 'address'):
            for attr, value in address_data.items():
                setattr(instance.address, attr, value)
            instance.address.save()
        else:
            PatientAddress.objects.create(patient=instance, **address_data)

        if hasattr(instance, 'document'):
            for attr, value in document_data.items():
                setattr(instance.document, attr, value)
            instance.document.save()
        else:
            PatientDocument.objects.create(patient=instance, **document_data)

        return instance
