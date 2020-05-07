from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse

import weasyprint

from .models import OrderItem, Order
from .forms import OrderCreateForm
from .tasks import order_created

from cart.cart import Cart


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.discount
            order.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])
            cart.clear()  # Clear the cart
            order_created.delay(order.id)  # Launch asynchronous task
            request.session['order_id'] = order.id  # Set the order in the session
            return redirect(reverse('payment:process'))  # Redirect for payment
    else:
        form = OrderCreateForm()

    context = {
        'cart': cart,
        'form': form,
    }
    return render(request, 'orders/order/create.html', context)


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    context = {
        'order': order
    }
    return render(request, 'admin/orders/order/detail.html', context)


@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('orders/order/pdf.html',
                            {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=order_{order.id}.pdf'
    weasyprint.HTML(string=html).write_pdf(response,
                                           stylesheets=[weasyprint.CSS(
                                               settings.STATIC_ROOT + 'css/pdf.css'
                                           )])
    return response