from django import forms
from admin_app.models import CategoryOffer, Banner


class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = "__all__"
        widgets = {
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

class BannerForm(forms.ModelForm):
    product_price = forms.DecimalField(label='Product Price', disabled=True, required=False)
    offer_percentage = forms.DecimalField(label='Offer Percentage', disabled=True, required=False)

    class Meta:
        model = Banner
        exclude = ['price', 'product_price', 'offer_percentage']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs and kwargs['instance']:
            instance = kwargs['instance']
            product = instance.product_color_image.product
            self.fields['product_price'].initial = product.offer_price
            self.fields['offer_percentage'].initial = product.percentage
        elif 'initial' in kwargs and 'product_color_image' in kwargs['initial']:
            product_color_image = kwargs['initial']['product_color_image']
            product = product_color_image.product
            self.fields['product_price'].initial = product.offer_price
            self.fields['offer_percentage'].initial = product.percentage



