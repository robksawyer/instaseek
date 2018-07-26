"""
Copyright © 2018 Valentin Berthelot.

This file is part of Instaseek.

Instaseek is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Instaseek is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Instaseek. If not, see <https://www.gnu.org/licenses/>.
"""

### System libs. ###
import sys
import os
import pickle
import random
import math

### Installed libs. ###
import pprint
import pandas as pd
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
from sklearn.utils import shuffle
from sklearn.model_selection import cross_val_score
import matplotlib.pyplot as plt
from tqdm import tqdm

sys.path.append(os.path.dirname(__file__))

### Custom libs. ###
from user import User
from sql_client import SqlClient

### Setup du PrettyPrinter, ainsi que des chemin d'accès aux fichiers. ###
pp = pprint.PrettyPrinter(indent = 2)

xl_path = os.path.join(os.path.dirname(__file__), '../res/iguserssample.xlsx')
model_path = os.path.join(os.path.dirname(__file__), '../models/classifier.model')
users_model_path = os.path.join(os.path.dirname(__file__), '../models/users_sample.model')
labels_model_path = os.path.join(os.path.dirname(__file__), '../models/labels.model')
ig_url = 'http://www.instagram.com/'

class Trainer(object):
	"""
	Classe d'entraînement du modèle de détection des influenceurs.
	"""

	def __init__(self, split_ratio = 0.8):
		"""
		__init__ function. On définit aussi les features que l'on va utiliser pour l'étude.
		"""

		super().__init__()
		self.key_features = [
			#'biographyscore',
			'commentscore', 
			'engagement',
			'followers',
			'followings',
			'nmedias',
			#'frequency',
			'lastpost',
			'usermentions',
			'colorfulness_std',
			'color_distorsion',
			'contrast_std'
		]
		self.features_array = list()
		self.labels = list()
		self.split_ratio = split_ratio
		self.users_array = list()

	def buildUsersModel(self):
		"""
		Construit la liste des utilisateurs utile pour l'entrainement, avec les features correspondantes.

				Args:
					(none)
				Returns:
					(none)
				
		"""

		self.sqlClient = SqlClient()

		### On récupère toutes les features nécessaires pour entraîner le modèle. ###
		self.user_model = User()
		users = self.user_model.getUserNames()

		### Si le modèle d'utilisateurs existe déjà, on l'ouvre. ###
		if os.path.isfile(users_model_path):
			with open(users_model_path, 'rb') as f:
				self.users_array = pickle.load(f)
		
		### Index du split. ###
		self.n_split = math.floor(self.split_ratio * len(self.users_array)) + 1

		### On parcourt le tableau des utilisateurs pour leur assigner les features. ###
		for user in tqdm(users):

			### Si l'utilisateur se trouve déjà dans le teableau, on n'a pas à réeffectuer le traitement. ###
			if user['user_name'] in [_user['username'] for _user in self.users_array]:
				continue
			self.user_model.username = user['user_name']

			### Récupère les features via la classe User. ###
			self.user_model.getUserInfoSQL()
			item = {
				'color_distorsion': self.user_model.color_distorsion,
				'colorfulness_std': self.user_model.colorfulness_std,
				'contrast_std': self.user_model.contrast_std,
				'lastpost': self.user_model.lastpost,
				'username': self.user_model.username,
				'frequency': self.user_model.frequency,
				'engagement': self.user_model.engagement,
				'followings': self.user_model.followings,
				'followers': self.user_model.followers,
				'nmedias': self.user_model.nmedias,
				'usermentions': self.user_model.usermentions,
				'brandpresence': self.user_model.brandpresence,
				'brandtypes': self.user_model.brandtypes,
				'commentscore': self.user_model.commentscore,
				'biographyscore': self.user_model.biographyscore,
				'label': self.user_model.label,
				'testset': self.user_model.testset
			}
			self.users_array.append(item)

			### Sauvegarde du modèle d'utilisateurs. ###
			with open(users_model_path, 'wb') as f:
				pickle.dump(self.users_array, f)

		### Assignation de la liste des features en tant que liste, et les labels correspondants. ###
		for user in self.users_array:
			features = list()
			for key in self.key_features:
				features.append(user[key])
			self.features_array.append(features)
			self.labels.append(user['label'])
		
		### On mélange les résultats pour ne pas avoir toujours les mêmes répartitions coup sur coup. ###
		self.features_array, self.labels, self.users_array = shuffle(self.features_array, self.labels, self.users_array, random_state = 0)

	def alterUsersModel(self):
		"""
		Au lieu de reconstruire le modèle d'utilisateurs à chaque fois, on change juste un champ pour des modifications occasionnelles.

				Args:
					(none)
				Returns:
					(none)
		"""
		
		self.sqlClient = SqlClient()
		self.user_model = User()

		### Charge le tableau des utilisateurs dont les features sont déjà extraites. ###
		if os.path.isfile(users_model_path):
			with open(users_model_path, 'rb') as f:
				users_array = pickle.load(f)

		adjusted_users = list()

		for user in users_array:
			
			self.sqlClient.openCursor()
			sqluser = self.sqlClient.getUser(user['username'])
			self.sqlClient.closeCursor()

			pp.pprint(sqluser)

			if sqluser['test_set'] == True:
				user['biographyscore'] = self.user_model.getBiographyScore(sqluser['biography'])
			adjusted_users.append(user)
			
		with open(users_model_path, 'wb') as f:
			pickle.dump(adjusted_users, f)

	def train(self):
		"""
		Entraînement du modèle de classification.
		
			Args:
				(none)
			
			Returns:
				(none)
		"""

		### Définition du classifieur de type Random Forest à 500 estimateurs. ###
		clf = RandomForestClassifier(n_estimators = 500)

		### On entraîne le classifieur avec le set d'entraînement (jusqu'à l'index n_split). ###
		clf.fit(self.features_array[:self.n_split], self.labels[:self.n_split])

		### On peut avoir l'importance des features dans la décision de la classification. ###
		importance = clf.feature_importances_

		### Score de la classification. ###
		scores = cross_val_score(clf, self.features_array, self.labels, cv = 5)
		print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

		### On calcule une prédiction pour la matrice de confusion et le rapport de classification. ###
		pred = clf.predict(self.features_array[self.n_split:])
		print('\n%s\n' % str(pred))
		print(confusion_matrix(self.labels[self.n_split:], pred))
		print('\n')

		### On affiche l'importance des critères de classification. ###
		for couple in zip(self.key_features, importance):
			print('________ %s' % str((couple[0], '%.2f%%' % float(100 * couple[1]))))
		print('\n')

		print(classification_report(self.labels[self.n_split:], pred))

		### Affichage des faux positifs et faux négatifs pour observer quels influenceurs sont mal détectés. ###
		#self.displayFPFN(pred)

		### Génération des probabilités (et non du vote à majorité) du Random Forest
		y_score = clf.predict_proba(self.features_array[self.n_split:])
		pred2 = [predclass[1] for predclass in y_score]

		### Construction de la courbe ROC. ###
		fpr, tpr, _ = roc_curve(self.labels[self.n_split:], pred2)
		### Aire sous la courbe. ###
		roc_auc = auc(fpr, tpr)

		### Affichage de la courbe ROC. ###
		plt.figure()
		lw = 2
		plt.plot(fpr, tpr, color='darkorange', lw=lw, label='ROC curve (area = %0.2f)' % roc_auc)
		plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
		plt.xlim([0.0, 1.0])
		plt.ylim([0.0, 1.05])
		plt.xlabel('False Positive Rate')
		plt.ylabel('True Positive Rate')
		plt.title('Receiver operating characteristic example')
		plt.legend(loc="lower right")
		plt.show()

		### Sauvegarde le classifieur en tant que modèle. ###
		with open(model_path, 'wb') as __f:
			pickle.dump(clf, __f)
		
	def displayFPFN(self, preds):
		"""
		Affiche les faux positifs et les faux négatifs pour une étude plus poussée des erreurs.

				Args:
					preds (int[]): : une liste des valeurs prédites.

				Returns:
					(none)
		"""

		### On instancie les listes des faux positifs et des faux négatifs. ###
		fp = list()
		fn = list()

		### On parcourt le tableau des prédictions pour obtenir les faux positifs et les faux négatifs. ###
		for index, pred in enumerate(preds):

			### Faux positifs. ###
			if pred == 1 and self.labels[self.n_split:][index] == 0:
				fp.append(self.users_array[self.n_split:][index]['username'])
			if pred == 0 and self.labels[self.n_split:][index] == 1:
				fn.append(self.users_array[self.n_split:][index]['username'])
		
		print('\nFaux positifs:\n\n')
		pp.pprint(fp)
		print('\n\nFaux négatifs:\n\n')
		pp.pprint(fn)

	def classify_user(self):
		"""
		Classe un utilisateur Instagram selon le modèle déjà entraîné.

				Args:
					(none)
				
				Returns:
					(none)
		"""

		### Ouvre le modèle de classification. ###
		with open(model_path, 'rb') as f:
			clf = pickle.load(f)

			### L'utilisateur entre un nom de profil Instagram afin d'utiliser le modèle de classification, et estimer si cette personne est un influenceur ou non. ###
			while True:
				username = input('Username: ')
				user = User()
				user.username = username
				user.getUserInfoIG()
				try:
					vector = [[
						#user.biographyscore, 
						user.commentscore,
						user.engagement,
						user.followers,
						user.followings,
						user.nmedias,
						user.lastpost,
						user.usermentions,
						user.colorfulness_std,
						user.color_distorsion,
						user.contrast_std
					]]

					### Prédiction. ###
					pred = clf.predict(vector)
					y_score = clf.predict_proba(vector)
					print('Result:\n\n%s\nScore: %s\n' % ('Influencer !' if pred == 1 else 'Not an influencer.', str(y_score[0][1] * 100) + '%'))
				
				except Exception as e:
					print('The user doesn\'t exist or has a private account. Please try again.')
					pass

if __name__ == "__main__":
	trainer = Trainer()
	trainer.buildUsersModel()
	trainer.train()