import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Dummy product data with image paths
PRODUCTS = {
    "p1": {
        "name": "Dummy Product A",
        "price": 10.00,
        "description": "A great dummy product.",
        "category": "Electronics",
        "image": "/home/ubuntu/dummy_images/product_a.png",
    },
    "p2": {
        "name": "Dummy Product B",
        "price": 25.50,
        "description": "Another fantastic dummy product.",
        "category": "Books",
        "image": "/home/ubuntu/dummy_images/product_b.png",
    },
    "p3": {
        "name": "Dummy Product C",
        "price": 5.00,
        "description": "Small and useful dummy product.",
        "category": "Home Goods",
        "image": "/home/ubuntu/dummy_images/product_c.jpg",
    },
}

# User carts and product index for carousel
user_carts = {}
user_product_index = {}

# States for conversation flow
PHONE_NUMBER, SHIPPING_ADDRESS, CONFIRM_ORDER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and main menu."""
    keyboard = [
        [InlineKeyboardButton("View Products", callback_data="view_products")],
        [InlineKeyboardButton("View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("Checkout", callback_data="checkout")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Dummy Store! Please choose an option:", reply_markup=reply_markup
    )

async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the first product with navigation buttons."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_product_index[user_id] = 0  # Start at the first product
    await display_product(update, context, user_id, 0)

async def display_product(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, index: int
) -> None:
    """Displays a single product with navigation buttons."""
    query = update.callback_query
    product_ids = list(PRODUCTS.keys())
    product_id = product_ids[index]
    product_info = PRODUCTS[product_id]

    # Create navigation buttons
    keyboard = [
        [
            InlineKeyboardButton("Previous", callback_data=f"prev_product_{index}"),
            InlineKeyboardButton("Next", callback_data=f"next_product_{index}"),
        ],
        [
            InlineKeyboardButton(
                f"Add {product_info['name']}", callback_data=f"add_to_cart_{product_id}"
            )
        ],
        [InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Prepare product message
    caption = f"{product_info['name']} - ${product_info['price']:.2f}\n{product_info['description']}\n\nProduct {index + 1}/{len(PRODUCTS)}"

    # Display or edit product message
    try:
        with open(product_info["image"], "rb") as f:
            if query:
                await query.message.edit_media(
                    media=InputMediaPhoto(media=f, caption=caption),
                    reply_markup=reply_markup,
                )
            else:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=f,
                    caption=caption,
                    reply_markup=reply_markup,
                )
    except FileNotFoundError:
        logger.error(f"Image file not found: {product_info['image']}")
        await (query.message if query else update.message).reply_text(
            f"Error: Image for {product_info['name']} not found."
        )
    except Exception as e:
        logger.error(f"Error displaying product: {e}")
        await (query.message if query else update.message).reply_text(
            "Error displaying product. Please try again."
        )

async def navigate_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles navigation between products."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    current_index = user_product_index.get(user_id, 0)
    product_ids = list(PRODUCTS.keys())
    max_index = len(product_ids) - 1

    if query.data.startswith("next_product_"):
        new_index = min(current_index + 1, max_index)
    elif query.data.startswith("prev_product_"):
        new_index = max(0, current_index - 1)
    else:
        return

    user_product_index[user_id] = new_index
    await display_product(update, context, user_id, new_index)

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds a product to the user's cart."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    product_id = query.data.replace("add_to_cart_", "")

    if product_id not in PRODUCTS:
        await query.message.reply_text("Invalid product selected.")
        return

    if user_id not in user_carts:
        user_carts[user_id] = {}

    user_carts[user_id][product_id] = user_carts[user_id].get(product_id, 0) + 1
    product_name = PRODUCTS[product_id]["name"]
    cart_count = sum(user_carts[user_id].values())

    await query.message.reply_text(
        f"{product_name} added to your cart!\n\nCurrent cart: {cart_count} items.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("View Cart", callback_data="view_cart")],
                [InlineKeyboardButton("Continue Shopping", callback_data="view_products")],
                [InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")],
            ]
        ),
    )

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the contents of the user's cart."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cart = user_carts.get(user_id, {})

    if not cart:
        await query.message.reply_text(
            "Your cart is empty!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("View Products", callback_data="view_products")],
                    [InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")],
                ]
            ),
        )
        return

    cart_text = "Your Cart:\n\n"
    total_price = 0.0
    keyboard = []

    for product_id, quantity in cart.items():
        product_info = PRODUCTS[product_id]
        name = product_info["name"]
        price = product_info["price"]
        item_price = price * quantity
        cart_text += f"- {name} (x{quantity}) - ${item_price:.2f}\n"
        total_price += item_price
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"Remove {name}", callback_data=f"remove_from_cart_{product_id}"
                )
            ]
        )

    cart_text += f"\nTotal: ${total_price:.2f}"
    keyboard.append([InlineKeyboardButton("Checkout", callback_data="checkout")])
    keyboard.append(
        [InlineKeyboardButton("Continue Shopping", callback_data="view_products")]
    )
    keyboard.append([InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(cart_text, reply_markup=reply_markup)

async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes a product from the user's cart."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    product_id = query.data.replace("remove_from_cart_", "")

    if user_id in user_carts and product_id in user_carts[user_id]:
        product_name = PRODUCTS[product_id]["name"]
        del user_carts[user_id][product_id]
        await query.message.reply_text(
            f"{product_name} removed from your cart.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("View Cart", callback_data="view_cart")],
                    [
                        InlineKeyboardButton(
                            "Continue Shopping", callback_data="view_products"
                        )
                    ],
                    [InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")],
                ]
            ),
        )
    else:
        await query.message.reply_text(
            "Item not found in cart.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("View Cart", callback_data="view_cart")],
                    [InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")],
                ]
            ),
        )

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the checkout process by asking for phone number."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cart = user_carts.get(user_id, {})

    if not cart:
        await query.message.reply_text(
            "Your cart is empty! Cannot checkout.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("View Products", callback_data="view_products")],
                    [InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")],
                ]
            ),
        )
        return ConversationHandler.END

    context.user_data["cart"] = cart
    await query.message.reply_text("Please provide your phone number for the order.")
    return PHONE_NUMBER

async def receive_phone_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives phone number and asks for shipping address."""
    user_id = update.effective_user.id
    phone_number = update.message.text
    logger.info(f"User {user_id} provided phone number: {phone_number}")

    if not re.match(r"^\+?\d{10,15}$", phone_number):
        await update.message.reply_text(
            "Invalid phone number. Please provide a valid number (e.g., +1234567890)."
        )
        return PHONE_NUMBER

    context.user_data["phone_number"] = phone_number
    await update.message.reply_text("Please provide your shipping address.")
    return SHIPPING_ADDRESS

async def receive_shipping_address(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives shipping address and asks for order confirmation."""
    user_id = update.effective_user.id
    shipping_address = update.message.text.strip()
    logger.info(f"User {user_id} provided shipping address: {shipping_address}")

    if not shipping_address or len(shipping_address) < 5:
        await update.message.reply_text(
            "Invalid shipping address. Please provide a valid address (at least 5 characters)."
        )
        return SHIPPING_ADDRESS

    context.user_data["shipping_address"] = shipping_address

    order_summary = "Please confirm your order details:\n\n"
    cart = context.user_data.get("cart", {})
    total_price = 0.0
    for product_id, quantity in cart.items():
        product_info = PRODUCTS[product_id]
        name = product_info["name"]
        price = product_info["price"]
        item_price = price * quantity
        order_summary += f"- {name} (x{quantity}) - ${item_price:.2f}\n"
        total_price += item_price

    phone_number = context.user_data.get("phone_number", "N/A")
    shipping_addr = context.user_data.get("shipping_address", "N/A")

    order_summary += f"\nTotal: ${total_price:.2f}"
    order_summary += f"\nPhone Number: {phone_number}"
    order_summary += f"\nShipping Address: {shipping_addr}"

    keyboard = [
        [InlineKeyboardButton("Confirm Order", callback_data="confirm_order")],
        [InlineKeyboardButton("Cancel Order", callback_data="cancel_order")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(order_summary, reply_markup=reply_markup)
    return CONFIRM_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalizes the order and clears the cart."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    logger.info(f"User {user_id} confirming order with data: {context.user_data}")

    if query.data == "confirm_order" and "cart" in context.user_data:
        # In a real scenario, save order to database and process payment
        user_carts.pop(user_id, None)  # Clear the cart
        context.user_data.clear()  # Clear temporary order data
        await query.edit_message_text(
            "Thank you for your order! Your order has been placed successfully.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")]]
            ),
        )
    elif query.data == "cancel_order":
        context.user_data.clear()  # Clear temporary order data
        await query.edit_message_text(
            "Your order has been cancelled.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back to Main Menu", callback_data="main_menu")]]
            ),
        )
    else:
        await query.edit_message_text(
            "Something went wrong. Please start over by typing /start."
        )
    return ConversationHandler.END

async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancels the conversation and returns to main menu."""
    await update.message.reply_text(
        "Checkout process cancelled. Use /start to return to the main menu."
    )
    context.user_data.clear()
    return ConversationHandler.END

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns to the main menu."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("View Products", callback_data="view_products")],
        [InlineKeyboardButton("View Cart", callback_data="view_cart")],
        [InlineKeyboardButton("Checkout", callback_data="checkout")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Welcome back to the Main Menu! Please choose an option:", reply_markup=reply_markup
    )

def main() -> None:
    """Run the bot."""
    load_dotenv()
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        logger.error("Bot token not found in environment variables.")
        return

    application = Application.builder().token(TOKEN).build()

    # Conversation handler for checkout
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout, pattern="^checkout$")],
        states={
            PHONE_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone_number)
            ],
            SHIPPING_ADDRESS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_shipping_address
                )
            ],
            CONFIRM_ORDER: [
                CallbackQueryHandler(
                    confirm_order, pattern="^(confirm_order|cancel_order)$"
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(
                filters.COMMAND | filters.PHOTO | filters.VIDEO | filters.Document.ALL,
                cancel_conversation,
            ),
        ],
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(view_products, pattern="^view_products$"))
    application.add_handler(
        CallbackQueryHandler(navigate_products, pattern="^(next_product_|prev_product_).*$")
    )
    application.add_handler(
        CallbackQueryHandler(add_to_cart, pattern="^add_to_cart_.*")
    )
    application.add_handler(CallbackQueryHandler(view_cart, pattern="^view_cart$"))
    application.add_handler(
        CallbackQueryHandler(remove_from_cart, pattern="^remove_from_cart_.*")
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

