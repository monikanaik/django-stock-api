from datetime import datetime
from django.db.models import F
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionListCreateView(ListCreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class AverageBuyPriceView(APIView):

    def get(self, request):
        try:
            trade_date = self.request.data['trade_date']
            trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()

            # Filter transactions until and including the given date
            transactions_until_date = Transaction.objects.filter(
                trade_date__lte=trade_date  # Include transactions on the specified date
            ).order_by('trade_date')

            if transactions_until_date.exists():
                total_qty = 0
                total_value = 0

                for transaction in transactions_until_date:
                    if transaction.trade_type == 'BUY':
                        total_qty += transaction.quantity
                        total_value += transaction.quantity * transaction.price_per_share

                    elif transaction.trade_type == 'SELL':
                        # Handle FIFO logic for selling shares
                        sell_qty = transaction.quantity

                        # Deduct sold shares from the earliest bought shares (FIFO)
                        while sell_qty > 0 and transactions_until_date.exists():
                            earliest_transaction = transactions_until_date.first()

                            if earliest_transaction.trade_type == 'BUY':
                                if earliest_transaction.quantity <= sell_qty:
                                    sell_qty -= earliest_transaction.quantity
                                    total_qty -= earliest_transaction.quantity
                                    total_value -= earliest_transaction.quantity * earliest_transaction.price_per_share
                                    earliest_transaction.delete()
                                else:
                                    earliest_transaction.quantity -= sell_qty
                                    total_qty -= sell_qty
                                    total_value -= sell_qty * earliest_transaction.price_per_share
                                    sell_qty = 0
                            else:
                                # Skip SELL transactions in the FIFO logic
                                earliest_transaction.delete()

                average_buy_price = total_value / total_qty if total_qty > 0 else 0
                balance_qty = total_qty

                result_data = {
                    'average_buy_price': round(average_buy_price, 2),
                    'balance_quantity': balance_qty,
                }

                return Response(result_data)
            else:
                return Response({"error": "No transactions found for the specified date."})
        except Exception as e:
            return Response({"error": str(e)})


class BuyTransactionView(APIView):
    def post(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(trade_type='BUY')  # Explicitly set BUY type
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class SellTransactionView(APIView):
    def post(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            # Apply FIFO logic to deduct shares from oldest transactions
            quantity_to_sell = serializer.validated_data['quantity']
            company_id = serializer.validated_data['company'].id

            # Retrieve the oldest BUY transactions
            buy_transactions = Transaction.objects.filter(
                company=company_id,
                trade_type='BUY',
                quantity__gt=0
            ).order_by('trade_date')

            for buy_transaction in buy_transactions:
                if quantity_to_sell >= buy_transaction.quantity:
                    quantity_to_sell -= buy_transaction.quantity
                    buy_transaction.quantity = 0
                else:
                    buy_transaction.quantity -= quantity_to_sell
                    quantity_to_sell = 0
                    break

                buy_transaction.save()

            serializer.save(trade_type='SELL')
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)


class SplitTransactionView(APIView):
    def post(self, request):
        try:
            serializer = TransactionSerializer(data=request.data)
            if serializer.is_valid():
                split_ratio = serializer.validated_data['split_ratio']
                company = serializer.validated_data['company']  # Re-enable company filtering
                # Retrieve existing BUY and SELL transactions for the company
                existing_transactions = Transaction.objects.filter(
                    company=company,  # Filter by company
                    trade_type__in=['BUY', 'SELL']
                )

                # Adjust quantities and prices efficiently using queryset updates
                Transaction.objects.filter(id__in=existing_transactions.values('id')).update(
                    quantity=F('quantity') * split_ratio,
                    price_per_share=F('price_per_share') / split_ratio
                )
                # Create a new SPLIT transaction to record the event
                serializer.save(trade_type='SPLIT')

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any exceptions that may occur during processing
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

