import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_invoice_insurance_covered_amount_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='idempotency_key',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='refund_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='payment',
            name='refund_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='refund_status',
            field=models.CharField(blank=True, choices=[
                ('', 'No Refund'),
                ('pending_approval', 'Pending Approval'),
                ('approved', 'Approved'),
                ('rejected', 'Rejected'),
            ], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='payment',
            name='refund_approved_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='refund_approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='PaymentGatewayTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('provider', models.CharField(choices=[
                    ('mpesa', 'M-Pesa (Daraja)'),
                    ('card', 'Card Processor'),
                    ('bank', 'Bank Feed'),
                ], max_length=16)),
                ('provider_reference', models.CharField(db_index=True, max_length=128)),
                ('provider_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('provider_timestamp', models.DateTimeField(blank=True, null=True)),
                ('raw_response', models.JSONField(blank=True, default=dict)),
                ('reconciliation_status', models.CharField(choices=[
                    ('unmatched', 'Unmatched'),
                    ('matched', 'Matched'),
                    ('disputed', 'Disputed'),
                ], default='unmatched', max_length=16)),
                ('reconciled_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('payment', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='gateway_transactions',
                    to='billing.payment',
                )),
                ('reconciled_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
