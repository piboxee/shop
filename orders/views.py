from django.shortcuts import render

from .models import OrderItem
from .forms import OrderCreateForm
from .tasks import order_created

from cart.cart import Cart


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])
            cart.clear()  # Clear the cart
            order_created.delay(order.id)  # Launch asynchronous task

            context = {
                'order': order
            }
            return render(request, 'orders/order/created.html', context)
    else:
        form = OrderCreateForm()

    context = {
        'cart': cart,
        'form': form,
    }
    return render(request, 'orders/order/create.html', context)
