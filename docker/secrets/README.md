# 🔐 Secrets Management

Ce répertoire contient les secrets sécurisés pour DATA_BOT v4.

## ⚠️ Important

**Ne jamais commiter les fichiers de secrets dans Git !**

## 📁 Fichiers générés automatiquement

Les fichiers suivants sont générés automatiquement par le script `deploy.sh` :

- `postgres_password.txt` - Mot de passe PostgreSQL
- `redis_password.txt` - Mot de passe Redis  
- `grafana_password.txt` - Mot de passe Grafana admin
- `ssl_cert.pem` - Certificat SSL (développement)
- `ssl_key.pem` - Clé privée SSL (développement)

## 📝 Fichiers à créer manuellement (production)

Pour la production, créez ces fichiers manuellement :

### Authentification SMTP
```bash
echo "your-smtp-password" > smtp_password.txt
```

### Clés AWS (pour sauvegardes)
```bash
echo "AKIAIOSFODNN7EXAMPLE" > aws_access_key.txt
echo "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" > aws_secret_key.txt
```

### Certificats SSL de production
```bash
# Copier vos certificats SSL de production
cp /path/to/prod/cert.pem ssl_cert.pem
cp /path/to/prod/key.pem ssl_key.pem
```

## 🔒 Sécurité

- Tous les fichiers ont des permissions 600 (lecture propriétaire uniquement)
- Les secrets sont montés en read-only dans les conteneurs
- Rotation automatique recommandée pour la production

## 🔄 Rotation des secrets

```bash
# Régénérer tous les secrets
rm -f *.txt *.pem
../scripts/deploy.sh deploy